import docx
import io
import re
import logging
import json
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


import os

def _get_semantic_map_from_llm(text: str) -> dict[str, str]:
    """
    Generates a semantic map by calling the OpenAI API.
    """
    logger.info("[Stage 1a] Generating semantic map via LLM.")

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable is not set.")

    client = OpenAI()

    system_prompt = """
You are an expert CV analyst. Your task is to read the provided CV text and generate a JSON object that maps specific text fragments to their corresponding Jinja2 placeholders.

**CV Structure and Naming Conventions:**

1.  **Header Section:**
    -   **Initials:** The acronym at the top (e.g., "RIN") maps to `{{ user_initials }}`.
    -   **Job Title:** e.g., "Développeuse web expérimentée" -> `{{ job_title }}`.
    -   **Experience Years:** e.g., "9 ans" -> `{{ years_of_experience }}`.
    -   **Client:** e.g., "Creative Web" -> `{{ current_client }}`.

2.  **Education & Certifications Table:**
    -   This section should be treated as a loop. Do not create placeholders for individual entries. Instead, identify the entire repeating block. For now, focus on simple text replacements. Advanced loop creation is a future step.

3.  **Technical Skills Block:**
    -   For each category (Backend, Frontend, etc.), map the list of skills to a single placeholder.
    -   Example: "PHP, Symfony, Laravel" -> `{{ backend_technologies | join(', ') }}`.

4.  **Professional Experience Section (Page 2):**
    -   This section contains multiple jobs and should be looped over with `{% for job in experiences %}`.
    -   For each job, identify:
        -   Job Title: e.g., "Développeuse Web — fullstack" -> `{{ job.title }}`.
        -   Company: `{{ job.company }}`.
        -   Dates: `{{ job.start_date }}`, `{{ job.end_date }}`.
        -   Tasks/Missions: These should be part of a nested loop `{% for task in job.tasks %}`.

**Your Task:**

-   Analyze the user-provided CV text.
-   Identify all text fragments that correspond to the fields listed above.
-   Create a JSON object where each key is the **exact text to be replaced** and the value is the **correct Jinja2 placeholder** according to the rules.
-   Do NOT invent placeholders. Only use the ones specified.
-   If a section should be a loop (like experiences), identify the individual elements for now (e.g., the first job title, first company name) for simple replacement. The full loop structure will be handled later.

**Output Format:** Your output MUST be ONLY a valid JSON object.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here is the CV text:\n\n```\n{text}\n```"},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        llm_output = response.choices[0].message.content
        semantic_map = json.loads(llm_output)
        logger.info("[Stage 1a] Successfully received and parsed semantic map from LLM.")
        return semantic_map
    except (RateLimitError, APIError) as e:
        logger.error(f"[Stage 1a] OpenAI API error: {e}")
        raise ValueError("The LLM service is currently unavailable or has hit a rate limit.")
    except Exception as e:
        logger.error(f"[Stage 1a] Failed to get semantic map from LLM: {e}", exc_info=True)
        raise


def _get_semantic_map_from_spacy(text: str, nlp_model: 'spacy.lang.en.English') -> dict[str, str]:
    """
    Generates a semantic map using spaCy and regex (fallback method).
    """
    logger.info("[Stage 1b] Generating semantic map via spaCy (fallback).")
    # This function contains the previous spaCy/regex logic
    doc = nlp_model(text)
    replacements = {}
    blocklist = {"I"}
    all_persons = list(dict.fromkeys([ent.text.strip() for ent in doc.ents if ent.label_ == "PER" and ent.text.strip() not in blocklist]))
    all_locations = list(dict.fromkeys([ent.text.strip() for ent in doc.ents if ent.label_ == "LOC" and ent.text.strip() not in blocklist]))
    if all_persons:
        other_persons = all_persons[1:]
        other_persons.sort(key=len, reverse=True)
        for person in other_persons:
            replacements[person] = "{{ person }}"
        replacements[all_persons[0]] = "{{ name }}"
    all_locations.sort(key=len, reverse=True)
    for loc in all_locations:
        replacements[loc] = "{{ location }}"
    emails = list(set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)))
    emails.sort(key=len, reverse=True)
    if emails:
        replacements[emails[0]] = "{{ email }}"
        for i, email in enumerate(emails[1:], 1):
            replacements[email] = f"{{ email_{i+1} }}"
    phones = list(set(re.findall(r'(?:\d{2}[-\.\s]?){4}\d{2}', text)))
    phones.sort(key=len, reverse=True)
    if phones:
        replacements[phones[0]] = "{{ phone }}"
        for i, phone in enumerate(phones[1:], 1):
            replacements[phone] = f"{{ phone_{i+1} }}"
    return replacements


def stage1_get_semantic_map(text: str, nlp_model: 'spacy.lang.en.English', use_llm: bool = True) -> dict[str, str]:
    """
    STAGE 1: Controller for generating the semantic map.
    """
    logger.info("[Stage 1] Starting semantic map generation.")
    if use_llm:
        try:
            return _get_semantic_map_from_llm(text)
        except Exception as e:
            logger.warning(f"[Stage 1] LLM-based map generation failed: {e}. Falling back to spaCy.")
            return _get_semantic_map_from_spacy(text, nlp_model)
    else:
        return _get_semantic_map_from_spacy(text, nlp_model)


def _replace_text_in_paragraph(paragraph: 'docx.text.paragraph.Paragraph', replacements: dict[str, str]):
    """Helper function to perform search-and-replace on runs within a paragraph."""
    sorted_replacements = sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True)
    for old, new in sorted_replacements:
        if old in paragraph.text:
            for run in paragraph.runs:
                if old in run.text:
                    run.text = run.text.replace(old, new)


def stage2_apply_annotations(docx_stream: io.BytesIO, semantic_map: dict[str, str]) -> io.BytesIO:
    """
    STAGE 2: Takes a .docx file and a semantic map and applies the annotations.
    """
    logger.info("[Stage 2] Applying annotations to DOCX.")
    try:
        doc = docx.Document(docx_stream)
    except Exception as e:
        logger.error(f"[Stage 2] Failed to load .docx file: {e}", exc_info=True)
        raise ValueError("Invalid or corrupted .docx file.")
    for paragraph in doc.paragraphs:
        _replace_text_in_paragraph(paragraph, semantic_map)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    _replace_text_in_paragraph(paragraph, semantic_map)
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
    semantic_map = stage1_get_semantic_map(full_text, nlp_model, use_llm=use_llm)
    if not semantic_map:
        logger.warning("No entities found to replace. Returning original document.")
        return docx_stream

    # Stage 2: Apply Annotations
    templated_docx_stream = stage2_apply_annotations(docx_stream, semantic_map)

    logger.info("Template conversion process completed successfully.")
    return templated_docx_stream
