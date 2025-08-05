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
    try:
        doc = docx.Document(docx_stream)
    except KeyError as e:
        # This specific KeyError from python-docx indicates a malformed package.
        # It's often because the file is not a true .docx file (e.g., a .doc renamed).
        logger.error(f"Failed to parse DOCX file, it may be corrupted or not a valid .docx format. Error: {e}")
        raise ValueError(
            "The file is not a valid .docx file. It may be corrupted, an older format (.doc), "
            "or a different file type with a .docx extension."
        )

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
You are a world-class expert CV analyst and Jinja2 template engineer. Your work must be perfect and syntactically correct. Your task is to read the provided CV text and generate a structured JSON object to be used for converting the CV into a template.

**Your Goal:**
Create a JSON object with two main keys: `simple_replacements` and `block_replacements`.

1.  **`simple_replacements`**: A dictionary for simple text-for-placeholder swaps (e.g., `{"John Doe": "{{ name }}"}`).
2.  **`block_replacements`**: A list of objects for complex sections that need to be replaced with Jinja2 loops. Each object must have `original_block` and `new_block` keys.

**CRITICAL JINJA2 SYNTAX & LOGIC RULES:**

1.  **PERFECT LOOPS:** Every `{% for ... %}` loop MUST be closed with `{% endfor %}`. This is non-negotiable. Nested loops require nested `endfor` tags.
2.  **CORRECT LOOP VARIABLES:** Inside a loop, variables MUST be prefixed with the loop variable. For example, inside `{% for job in experiences %}`, you must use `{{ job.title }}`, NOT `{{ title }}`.
3.  **JOIN FILTERS:** For lists of skills, use the `| join(', ')` filter. Example: `{{ backend_technologies | join(', ') }}`.
4.  **NO INVENTED PLACEHOLDERS:** Only use the standard, logical placeholder names demonstrated in the example.

**Perfect Example of a `block_replacements` entry:**
-   **Input Text:** "Développeuse Web – fullstack\nCreative Web\nOctobre 2018\nOctobre 2025\nMISSIONS :\n- Task 1\n- Task 2"
-   **Required `new_block` code:**
    ```jinja2
{% for job in experiences %}
Développeuse Web – fullstack
{{ job.company }}
{{ job.start_date }} – {{ job.end_date }}

MISSIONS :
{% for task in job.tasks %}
- {{ task }}
{% endfor %}
{% endfor %}
    ```
    (Note the two `endfor` tags for the nested loops).

**Final Instruction:**
Before creating the final JSON, double-check all generated Jinja2 code in the `new_block` values for syntax errors. Your output must be flawless. Your output MUST be ONLY a valid JSON object.
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
    # Only try to remove the paragraph if it has a parent.
    if p.getparent() is not None:
        p.getparent().remove(p)
        # Set the paragraph's element to None to indicate it's been removed
        paragraph._p = paragraph._element = None
    else:
        # This can happen if the paragraph was already part of a block that got deleted.
        logger.warning("Attempted to delete a paragraph that has already been removed or orphaned. Skipping.")

def secure_loop_block(var_name: str, iterable: str, body: str) -> str:
    """
    Injects a loop block with guaranteed {% for %} and {% endfor %} tags.
    """
    return f"""{{% for {var_name} in {iterable} %}}
{body.strip()}
{{% endfor %}}"""

def validate_and_clean_paragraph_text(text: str) -> str:
    """
    Cleans and validates Jinja2 syntax within a single line of text.
    - Fixes common formatting errors like spaces around colons.
    - Warns about unexpected variable names.
    """
    # Fix badly formatted colons in dictionaries, e.g., {{ key }} : {{ value }}
    bad_colon_pattern = re.compile(r"(\{\{[^}]+?\}\} ?\: ?\{\{[^}]+?\}\})")
    for match in bad_colon_pattern.finditer(text):
        original_match = match.group(1)
        corrected_match = original_match.replace(" :", ":").replace(": ", ":")
        text = text.replace(original_match, corrected_match)
        logger.debug(f"Corrected colon formatting: '{original_match}' -> '{corrected_match}'")

    # Warn about unexpected variable names
    variable_pattern = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")
    allowed_vars = [
        "education.title", "education.institution", "education.date",
        "job.title", "job.company", "job.start_date", "job.end_date", "job.description",
        "skill.category", "skill.name",
        "project.name", "project.description",
        "name", "title", "email", "phone", "location"
    ]
    # A simple check to avoid warnings on loop variables like 'job.title'
    # by checking the root object name.
    allowed_roots = ['job', 'education', 'skill', 'project']

    for match in variable_pattern.finditer(text):
        variable_name = match.group(1).strip()
        # Check if the variable is in the allowed list or if its root is an allowed loop variable
        if variable_name not in allowed_vars and variable_name.split('.')[0] not in allowed_roots:
             logger.warning(f"Unexpected variable found in template: '{{{{ {variable_name} }}}}'")

    return text

def _normalize_text_for_match(text: str) -> str:
    """Aggressively normalizes text to ensure a match."""
    # Replace various whitespace chars with a single space
    text = re.sub(r'[\s\u00A0\t]+', ' ', text)
    # Remove non-breaking space specifically if it's attached to words
    text = text.replace(' ', ' ')
    # Optional: remove punctuation, but can be risky
    # text = re.sub(r'[^\w\s]', '', text)
    return text.strip()

def _replace_text_block(paragraphs: list, original_block: str, new_block: str):
    """
    Finds a multi-paragraph block of text within a list of paragraphs and replaces it.
    """
    logger.info(f"Attempting to replace block starting with: '{original_block.splitlines()[0] if original_block else ''}...'")

    # Normalize the target block from the LLM
    original_lines = [line.strip() for line in original_block.splitlines() if line.strip()]
    normalized_original_block = " ".join(original_lines)
    normalized_original_block = _normalize_text_for_match(normalized_original_block)

    # Find the start paragraph
    start_para_index = -1
    for i, p in enumerate(paragraphs):
        if _normalize_text_for_match(p.text) == _normalize_text_for_match(original_lines[0]):
            start_para_index = i
            break

    if start_para_index == -1:
        logger.warning("Could not find the starting paragraph of the block.")
        return False

    # Collect subsequent paragraphs to match the full block
    collected_paras = []
    collected_text_normalized = []
    for i in range(start_para_index, len(paragraphs)):
        p = paragraphs[i]
        p_text_norm = _normalize_text_for_match(p.text)
        if not p_text_norm:
            continue

        collected_paras.append(p)
        collected_text_normalized.append(p_text_norm)

        # Check if the collected block matches the target block
        current_block_normalized = " ".join(collected_text_normalized)
        if current_block_normalized == normalized_original_block:
            logger.info(f"Found matching block of {len(collected_paras)} paragraphs. Replacing.")

            # Perform replacement
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
    This version includes programmatic validation and cleaning of Jinja2 syntax.
    """
    logger.info("[Stage 2] Applying annotations to DOCX with validation.")
    try:
        doc = docx.Document(docx_stream)
    except Exception as e:
        logger.error(f"[Stage 2] Failed to load .docx file: {e}", exc_info=True)
        raise ValueError("Invalid or corrupted .docx file.")

    # Create a list of all paragraphs for simple replacements
    all_paragraphs = list(doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                all_paragraphs.extend(cell.paragraphs)

    # Handle simple replacements first
    simple_replacements = semantic_map.get("simple_replacements", {})
    if simple_replacements:
        for paragraph in all_paragraphs:
            _replace_text_in_paragraph(paragraph, simple_replacements)

    # Handle block replacements with programmatic security
    block_replacements = semantic_map.get("block_replacements", [])
    loop_parser = re.compile(r"{%\s*for\s+(\w+)\s+in\s+([\w\.]+)\s*%}(.*?){%\s*endfor\s*%}", re.DOTALL)

    if block_replacements:
        for block in block_replacements:
            original_llm_block = block["new_block"]
            match = loop_parser.search(original_llm_block)

            if match:
                var_name, iterable, body = match.groups()
                # Use the secure function to guarantee correct loop structure
                safe_block = secure_loop_block(var_name, iterable, body)
                logger.debug(f"Injected secure loop block:\n{safe_block}")
                block_to_inject = safe_block
            else:
                logger.warning(f"Could not parse loop from LLM output. Using raw block as fallback:\n{original_llm_block}")
                block_to_inject = original_llm_block

            # The document is modified in place, so we must re-fetch paragraphs each time
            # to get an up-to-date representation of the document structure.
            current_paragraphs = list(doc.paragraphs)
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        current_paragraphs.extend(cell.paragraphs)
            _replace_text_block(current_paragraphs, block["original_block"], block_to_inject)

    # Final cleaning and validation pass
    logger.info("[Stage 2] Performing final validation and cleaning pass.")
    final_paragraphs = list(doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                final_paragraphs.extend(cell.paragraphs)

    for para in final_paragraphs:
        original_text = para.text
        cleaned_text = validate_and_clean_paragraph_text(original_text)
        if original_text != cleaned_text:
            # This is a simplification; replacing runs might be better for preserving formatting.
            para.text = cleaned_text

    target_stream = io.BytesIO()
    doc.save(target_stream)
    target_stream.seek(0)
    logger.info("[Stage 2] Annotation application and validation successful.")
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
