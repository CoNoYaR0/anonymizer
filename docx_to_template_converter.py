import docx
import io
import re
import logging
import json
import os
from openai import OpenAI, RateLimitError, APIError
from spacy.tokens import Doc

# Configure logger
logger = logging.getLogger(__name__)

def _extract_text_from_docx(docx_stream: io.BytesIO) -> str:
    """Extracts all text from a .docx file stream."""
    doc = docx.Document(docx_stream)
    full_text = "\n".join([p.text for p in doc.paragraphs])
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                full_text += "\n" + cell.text
    docx_stream.seek(0)
    return full_text

def _get_structured_data_from_llm(text: str) -> dict:
    """
    STAGE 1: Calls an LLM to extract structured data from the CV text.
    """
    logger.info("[Stage 1] Getting structured data from LLM.")

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable is not set.")

    client = OpenAI()

    system_prompt = """
You are an expert data extraction assistant. Your task is to analyze the raw text from a CV and convert it into a structured JSON object.

- Scrutinize the text to identify all professional experiences, skills, education, and personal details.
- Populate the JSON object according to the schema below.
- Ensure the final output is ONLY a valid JSON object.

**JSON Schema:**
{
  "name": "string",
  "job_title": "string",
  "years_of_experience": "string",
  "current_client": "string",
  "contact": {
    "email": "string",
    "phone": "string"
  },
  "skills": [
    {
      "category": "string (e.g., 'Développement Backend')",
      "technologies": "string (comma-separated list, e.g., 'Symfony, Java, Spring Boot')"
    }
  ],
  "educations": [
    {
      "period": "string",
      "degree": "string",
      "institution": "string"
    }
  ],
  "experiences": [
    {
      "title": "string",
      "company": "string",
      "period": "string",
      "tasks": ["string"]
    }
  ]
}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here is the CV text:\n\n```\n{text}\n```"},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        llm_output = response.choices[0].message.content
        structured_data = json.loads(llm_output)
        logger.info("[Stage 1] Successfully received structured data from LLM.")
        return structured_data
    except Exception as e:
        logger.error(f"[Stage 1] Failed to get structured data from LLM: {e}", exc_info=True)
        raise

def _build_replacement_map(data: dict, original_text: str) -> dict:
    """
    Builds the semantic map for replacements from the structured data.
    The Jinja2 code is generated here, in Python, for reliability.
    """
    semantic_map = {"simple_replacements": {}, "block_replacements": []}

    # Simple replacements
    if data.get("name"):
        semantic_map["simple_replacements"][data["name"]] = "{{ user_initials }}"
    if data.get("job_title"):
        semantic_map["simple_replacements"][data["job_title"]] = "{{ job_title }}"
    if data.get("contact", {}).get("email"):
        semantic_map["simple_replacements"][data["contact"]["email"]] = "{{ email }}"
    if data.get("contact", {}).get("phone"):
        semantic_map["simple_replacements"][data["contact"]["phone"]] = "{{ phone }}"
    # ... add other simple fields here

    # Block replacement for skills
    if data.get("skills"):
        original_block_lines = []
        for skill_cat in data["skills"]:
            original_block_lines.append(f"{skill_cat['category']} : {skill_cat['technologies']}")
        original_block = "\n".join(original_block_lines)

        new_block = "{% for skill_cat in skills %}\n"
        new_block += "{{ skill_cat.category }} : {{ skill_cat.technologies | join(', ') }}\n"
        new_block += "{% endfor %}"

        semantic_map["block_replacements"].append({
            "original_block": original_block,
            "new_block": new_block
        })

    # Block replacement for experiences
    if data.get("experiences"):
        original_block_lines = []
        for exp in data["experiences"]:
            original_block_lines.append(exp["title"])
            original_block_lines.append(exp["company"])
            original_block_lines.append(exp["period"])
            original_block_lines.append("MISSIONS :")
            original_block_lines.extend(exp["tasks"])
        original_block = "\n".join(original_block_lines)

        new_block = "{% for job in experiences %}\n"
        new_block += "{{ job.title }}\n{{ job.company }}\n{{ job.period }}\n"
        new_block += "MISSIONS :\n"
        new_block += "{% for task in job.tasks %}\n- {{ task }}\n{% endfor %}\n"
        new_block += "{% endfor %}"

        semantic_map["block_replacements"].append({
            "original_block": original_block,
            "new_block": new_block
        })

    return semantic_map

def _delete_paragraph(paragraph):
    p = paragraph._element
    p.getparent().remove(p)
    paragraph._p = paragraph._element = None

def _replace_text_block(paragraphs: list, original_block: str, new_block: str):
    # This function remains the same as the last robust version
    logger.info(f"Attempting to replace block starting with: '{original_block.splitlines()[0] if original_block else ''}...'")
    normalized_original_block = "\n".join(line.strip() for line in original_block.splitlines() if line.strip())

    for i in range(len(paragraphs)):
        if paragraphs[i].text.strip() == normalized_original_block.split('\n')[0]:
            collected_paras = []
            collected_text = []
            for j in range(i, len(paragraphs)):
                para_text = paragraphs[j].text.strip()
                if not para_text: continue
                collected_paras.append(paragraphs[j])
                collected_text.append(para_text)
                current_block_text = "\n".join(collected_text)
                if current_block_text == normalized_original_block:
                    logger.info(f"Found matching block of {len(collected_paras)} paragraphs. Replacing.")
                    first_para = collected_paras[0]
                    first_para.text = ''
                    first_para.add_run(new_block)
                    for para_to_delete in collected_paras[1:]:
                        _delete_paragraph(para_to_delete)
                    logger.info("Block replacement successful.")
                    return True
    logger.warning("Could not find a matching block in the document to replace.")
    return False

def stage2_apply_annotations(docx_stream: io.BytesIO, semantic_map: dict) -> io.BytesIO:
    """
    STAGE 2: Takes a .docx file and a semantic map, and applies the annotations.
    """
    logger.info("[Stage 2] Applying annotations to DOCX.")
    doc = docx.Document(docx_stream)

    # Block replacements must be done first, as they change the doc structure
    block_replacements = semantic_map.get("block_replacements", [])
    if block_replacements:
        for block in block_replacements:
            all_paragraphs = doc.paragraphs + [p for t in doc.tables for r in t.rows for c in r.cells for p in c.paragraphs]
            _replace_text_block(all_paragraphs, block["original_block"], block["new_block"])

    # Simple replacements are done second
    simple_replacements = semantic_map.get("simple_replacements", {})
    if simple_replacements:
        all_paragraphs = doc.paragraphs + [p for t in doc.tables for r in t.rows for c in r.cells for p in c.paragraphs]
        for paragraph in all_paragraphs:
            for old, new in simple_replacements.items():
                if old in paragraph.text:
                    for run in paragraph.runs:
                        if old in run.text:
                            run.text = run.text.replace(old, new)

    target_stream = io.BytesIO()
    doc.save(target_stream)
    target_stream.seek(0)
    logger.info("[Stage 2] Annotation application successful.")
    return target_stream

def convert_docx_to_template(docx_stream: io.BytesIO, nlp_model: 'spacy.lang.en.English', use_llm: bool = True) -> io.BytesIO:
    """
    Orchestrates the new, more reliable multi-stage process.
    """
    logger.info("Starting new reliable template conversion process.")
    full_text = _extract_text_from_docx(docx_stream)
    if not full_text.strip():
        return docx_stream

    # Stage 1: Get structured data from LLM
    structured_data = _get_structured_data_from_llm(full_text)

    # New Step: Build the replacement map from the structured data
    semantic_map = _build_replacement_map(structured_data, full_text)

    if not semantic_map.get("simple_replacements") and not semantic_map.get("block_replacements"):
        logger.warning("Could not build a replacement map from the data. Returning original document.")
        return docx_stream

    # Stage 2: Apply programmatically-generated annotations
    templated_docx_stream = stage2_apply_annotations(docx_stream, semantic_map)

    logger.info("Template conversion process completed successfully.")
    return templated_docx_stream
