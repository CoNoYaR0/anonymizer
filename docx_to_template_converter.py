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

def _get_semantic_map_from_llm(text: str) -> dict:
    """
    Generates a structured semantic map by calling the OpenAI API.
    The map includes simple replacements and complex block replacements for loops.
    """
    logger.info("[Stage 1a] Generating semantic map via LLM.")

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable is not set.")

    client = OpenAI()

    system_prompt = """
You are an expert CV analyst and Jinja2 template engineer. Your task is to read the provided CV text and generate a structured JSON object to be used for converting the CV into a template.

**Your Goal:**
Create a JSON object with two main keys: `simple_replacements` and `block_replacements`.

1.  **`simple_replacements`**: A dictionary for simple text-for-placeholder swaps.
    -   Identify names, emails, phones, single skills, etc.
    -   Use the naming convention provided (e.g., `{{ user_initials }}`, `{{ job_title }}`).
    -   The key should be the exact text to replace, and the value is the placeholder.

2.  **`block_replacements`**: A list of objects for complex sections that need to be replaced with Jinja2 loops.
    -   Each object in the list should have two keys: `original_block` and `new_block`.
    -   `original_block`: A string containing the entire, multi-line text of the section to be replaced (e.g., all job experiences).
    -   `new_block`: A string containing the full Jinja2 loop code that should replace the original block.

**Example Task:**
-   **Input Text:** "Développeuse Web – fullstack\nCreative Web\nOctobre 2018\nOctobre 2025\nMISSIONS :\n- Task 1\n- Task 2"
-   **Required `block_replacements` entry:**
    ```json
    {
      "original_block": "Développeuse Web – fullstack\nCreative Web\nOctobre 2018\nOctobre 2025\nMISSIONS :\n- Task 1\n- Task 2",
      "new_block": "{% for job in experiences %}\n{{ job.title }}\n{{ job.company }}\n{{ job.start_date }} - {{ job.end_date }}\n\nMISSIONS :\n{% for task in job.tasks %}\n- {{ task }}\n{% endfor %}\n{% endfor %}"
    }
    ```

**Output Format:**
Your output MUST be ONLY a valid JSON object adhering to this structure.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here is the CV text to be templated:\n\n```\n{text}\n```"},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        llm_output = response.choices[0].message.content
        semantic_map = json.loads(llm_output)
        logger.info("[Stage 1a] Successfully received structured semantic map from LLM.")
        return semantic_map
    except (RateLimitError, APIError) as e:
        logger.error(f"[Stage 1a] OpenAI API error: {e}")
        raise ValueError("The LLM service is currently unavailable or has hit a rate limit.")
    except Exception as e:
        logger.error(f"[Stage 1a] Failed to get semantic map from LLM: {e}", exc_info=True)
        raise

def stage1_get_semantic_map(text: str, use_llm: bool = True) -> dict:
    """
    STAGE 1: Controller for generating the semantic map.
    """
    logger.info("[Stage 1] Starting semantic map generation.")
    if use_llm:
        return _get_semantic_map_from_llm(text)
    else:
        logger.warning("[Stage 1] Non-LLM method is not supported for this advanced templating. LLM is required.")
        return {"simple_replacements": {}, "block_replacements": []}


def _replace_text_in_paragraph(paragraph: 'docx.text.paragraph.Paragraph', replacements: dict[str, str]):
    """Helper function to perform simple search-and-replace on runs within a paragraph."""
    sorted_replacements = sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True)
    for old, new in sorted_replacements:
        if old in paragraph.text:
            for run in paragraph.runs:
                if old in run.text:
                    run.text = run.text.replace(old, new)

def _delete_paragraph(paragraph):
    """Helper function to delete a paragraph from its parent."""
    p = paragraph._element
    p.getparent().remove(p)
    paragraph._p = paragraph._element = None

def _replace_text_block(paragraphs: list, original_block: str, new_block: str):
    """
    Finds a multi-paragraph block of text within a list of paragraphs and replaces it.
    """
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
    try:
        doc = docx.Document(docx_stream)
    except Exception as e:
        logger.error(f"[Stage 2] Failed to load .docx file: {e}", exc_info=True)
        raise ValueError("Invalid or corrupted .docx file.")

    # Create a single list of all paragraphs in the document, in order
    all_paragraphs = []
    for para in doc.paragraphs:
        all_paragraphs.append(para)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    all_paragraphs.append(para)

    # Handle simple replacements first
    simple_replacements = semantic_map.get("simple_replacements", {})
    if simple_replacements:
        for paragraph in all_paragraphs:
            _replace_text_in_paragraph(paragraph, simple_replacements)

    # Handle block replacements
    block_replacements = semantic_map.get("block_replacements", [])
    if block_replacements:
        for block in block_replacements:
            # We need to re-fetch all paragraphs for each block replacement as the
            # document structure changes after deletion.
            current_paragraphs = []
            for para in doc.paragraphs:
                current_paragraphs.append(para)
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for para in cell.paragraphs:
                            current_paragraphs.append(para)
            _replace_text_block(current_paragraphs, block["original_block"], block["new_block"])

    target_stream = io.BytesIO()
    doc.save(target_stream)
    target_stream.seek(0)
    logger.info("[Stage 2] Annotation application successful.")
    return target_stream


def convert_docx_to_template(docx_stream: io.BytesIO, nlp_model: 'spacy.lang.en.English', use_llm: bool = True) -> io.BytesIO:
    """
    Orchestrates the multi-stage process of converting a DOCX to a Jinja2 template.
    """
    logger.info("Starting multi-stage template conversion process.")
    full_text = _extract_text_from_docx(docx_stream)
    if not full_text.strip():
        logger.warning("No text found in the document. Returning original file.")
        return docx_stream

    # Stage 1: Get Semantic Map
    semantic_map = stage1_get_semantic_map(full_text, use_llm=use_llm)
    if not semantic_map.get("simple_replacements") and not semantic_map.get("block_replacements"):
        logger.warning("No entities found to replace. Returning original document.")
        return docx_stream

    # Stage 2: Apply Annotations
    templated_docx_stream = stage2_apply_annotations(docx_stream, semantic_map)

    logger.info("Template conversion process completed successfully.")
    return templated_docx_stream
