import io
import os
import logging
import time
import base64
import json
import hashlib
from typing import IO, Optional
import httpx
from openai import OpenAI
from liquid import Liquid
from bs4 import BeautifulSoup
from database import get_db_connection, release_db_connection


# --- Configuration ---
logger = logging.getLogger(__name__)
CONVERTIO_API_KEY = os.getenv("CONVERTIO_API_KEY")
if not CONVERTIO_API_KEY:
    logger.critical("CONVERTIO_API_KEY environment variable is not set. This is a fatal error.")
    raise RuntimeError("CONVERTIO_API_KEY is not configured, cannot proceed with template conversion.")
CONVERTIO_API_URL = "https://api.convertio.co/convert"

# --- Database and Caching Functions (Mockable) ---

def _get_file_hash(file_stream: IO[bytes]) -> str:
    """Calculates the SHA-256 hash of a file stream."""
    logger.debug("Entering _get_file_hash")
    hash_sha256 = hashlib.sha256()
    # Reset stream position to the beginning
    file_stream.seek(0)
    # Read file in chunks to handle large files
    for chunk in iter(lambda: file_stream.read(4096), b""):
        hash_sha256.update(chunk)
    # Reset stream position again for subsequent operations
    file_stream.seek(0)
    file_hash = hash_sha256.hexdigest()
    logger.debug(f"Exiting _get_file_hash with hash: {file_hash}")
    return file_hash

def _get_cached_html(file_hash: str) -> Optional[str]:
    """
    Retrieves cached HTML content from the database.
    """
    logger.debug(f"Entering _get_cached_html with hash: {file_hash}")
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            logger.error("Could not get a database connection.")
            return None
        with conn.cursor() as cur:
            cur.execute(
                "SELECT html_content FROM html_conversion_cache WHERE file_hash = %s",
                (file_hash,)
            )
            result = cur.fetchone()
            if result:
                logger.info(f"Cache hit for hash: {file_hash}")
                return result[0]
            else:
                logger.info(f"Cache miss for hash: {file_hash}")
                return None
    except Exception as e:
        logger.error(f"Error retrieving cached HTML: {e}", exc_info=True)
        return None
    finally:
        if conn:
            release_db_connection(conn)

def _cache_html(file_hash: str, html_content: str):
    """
    Saves new HTML content to the database cache.
    """
    logger.debug(f"Entering _cache_html with hash: {file_hash}")
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            logger.error("Could not get a database connection for caching.")
            return

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO html_conversion_cache (file_hash, html_content)
                VALUES (%s, %s)
                ON CONFLICT (file_hash) DO NOTHING;
                """,
                (file_hash, html_content)
            )
            conn.commit()
            logger.info(f"Successfully cached HTML for hash: {file_hash}")
    except Exception as e:
        logger.error(f"Error caching HTML: {e}", exc_info=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            release_db_connection(conn)

# --- Private Helper Functions: Convertio Workflow ---

def _start_conversion(file_stream: IO[bytes], filename: str) -> str:
    """Starts a new conversion on the Convertio API."""
    logger.debug(f"Entering _start_conversion with filename: {filename}")
    if not CONVERTIO_API_KEY:
        raise ValueError("CONVERTIO_API_KEY environment variable is not set.")
    logger.info(f"Starting Convertio conversion for '{filename}'.")
    file_base64 = base64.b64encode(file_stream.read()).decode('utf-8')
    payload = {
        "apikey": CONVERTIO_API_KEY, "input": "base64", "file": file_base64,
        "filename": filename, "outputformat": "html"
    }
    with httpx.Client() as client:
        response = client.post(CONVERTIO_API_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Convertio start conversion response: {data}")
        if data.get("status") == "error":
            raise ValueError(f"Convertio API error: {data.get('error')}")
        conversion_id = data.get("data", {}).get("id")
        if not conversion_id:
            raise ValueError("Failed to get a conversion ID from Convertio.")
        logger.info(f"Successfully started conversion with ID: {conversion_id}")
        logger.debug(f"Exiting _start_conversion with conversion_id: {conversion_id}")
        return conversion_id

def _poll_conversion_status(conversion_id: str) -> str:
    """Polls Convertio for conversion status and returns the output file URL."""
    logger.debug(f"Entering _poll_conversion_status with conversion_id: {conversion_id}")
    logger.info(f"Polling status for conversion ID: {conversion_id}")
    status_url = f"{CONVERTIO_API_URL}/{conversion_id}/status"
    with httpx.Client() as client:
        while True:
            response = client.get(status_url, timeout=30)
            response.raise_for_status()
            data = response.json()
            logger.debug(f"Convertio poll status response: {data}")
            if data.get("status") == "error":
                raise ValueError(f"Convertio status check failed: {data.get('error')}")
            step = data.get("data", {}).get("step")
            logger.info(f"Conversion status: {step} ({data.get('data', {}).get('step_percent', 0)}%)")
            if step == "finish":
                output_url = data.get("data", {}).get("output", {}).get("url")
                if not output_url:
                    raise ValueError("Conversion finished, but no output URL was provided.")
                logger.info("Conversion finished successfully.")
                logger.debug(f"Exiting _poll_conversion_status with output_url: {output_url}")
                return output_url
            elif step == "error":
                raise ValueError("Conversion failed at Convertio.")
            time.sleep(2)

def _download_html_content(url: str) -> str:
    """Downloads the HTML content from the given URL."""
    logger.debug(f"Entering _download_html_content with url: {url}")
    logger.info(f"Downloading converted HTML from: {url}")
    with httpx.Client() as client:
        response = client.get(url, timeout=60, follow_redirects=True)
        response.raise_for_status()
        html_content = response.text
        logger.debug(f"Exiting _download_html_content with html_content (first 100 chars): {html_content[:100]}")
        return html_content

# --- Private Helper Functions: Templating Workflow ---

def _get_replacement_map_from_llm(html_content: str) -> dict:
    """
    Extracts text from HTML, sends it to an LLM, and gets back a map of
    static text to its corresponding Liquid placeholder.
    """
    logger.debug("Entering _get_replacement_map_from_llm")
    logger.info("Extracting text from HTML for LLM processing.")
    soup = BeautifulSoup(html_content, 'html.parser')
    text_content = soup.get_text(separator='\n', strip=True)
    logger.debug(f"Extracted text_content: {text_content}")

    if not text_content.strip():
        raise ValueError("No text content found in the HTML to process.")

    logger.info("Sending extracted text to LLM to get replacement map.")
    client = OpenAI()
    system_prompt = """
You are an expert data analyst. Your task is to read the raw text from a CV and generate a JSON object that maps static, personal information to its dynamic Liquid placeholder.

**Your Goal:**
Create a JSON object where each key is a string of static text found in the CV (like a specific name, company, or job title) and its value is the corresponding, correct Liquid placeholder.

**CRITICAL RULES:**
1.  **JSON-ONLY OUTPUT:** Your output MUST be ONLY a valid JSON object.
2.  **PRESERVE ORIGINAL TEXT:** The JSON keys MUST EXACTLY MATCH the original text from the input, including punctuation and casing.
3.  **USE STANDARD PLACEHOLDERS:** Use standard placeholders like `{{ name }}`, `{{ title }}`, `{{ job.company }}`, etc. Do NOT wrap entire sections in `{% for %}` loops. The goal is to identify individual pieces of text that should be dynamic.

**Example:**
-   **Input Text:** "John Doe\nSenior Developer\nExample Corp"
-   **Required JSON Output:**
    ```json
    {
      "John Doe": "{{ name }}",
      "Senior Developer": "{{ title }}",
      "Example Corp": "{{ company_name }}"
    }
    ```
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here is the raw CV text:\n\n```\n{text_content}\n```"},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        replacement_map_str = response.choices[0].message.content
        logger.debug(f"LLM response: {replacement_map_str}")
        replacement_map = json.loads(replacement_map_str)
        logger.info("Successfully received replacement map from LLM.")
        logger.debug(f"Exiting _get_replacement_map_from_llm with replacement_map: {replacement_map}")
        return replacement_map
    except Exception as e:
        logger.error(f"LLM replacement map generation failed: {e}", exc_info=True)
        raise ValueError("Failed to generate replacement map using the LLM.")

def _apply_replacements_to_html(html_content: str, replacement_map: dict) -> str:
    """
    Performs a DOM-aware search and replace on the HTML content.
    It iterates through text nodes to replace content without breaking the HTML structure.
    """
    logger.debug(f"Entering _apply_replacements_to_html with replacement_map: {replacement_map}")
    logger.info(f"Applying {len(replacement_map)} replacements to the HTML using DOM-aware method.")
    soup = BeautifulSoup(html_content, 'html.parser')

    for original_text, liquid_placeholder in replacement_map.items():
        # Find all text nodes that contain the original text
        for text_node in soup.find_all(text=lambda t: t and original_text in t):
            # Replace only the matching text, not the entire node
            if text_node.string:
                new_string = text_node.string.replace(original_text, liquid_placeholder)
                text_node.string.replace_with(new_string)

    final_html = str(soup)
    logger.debug(f"Exiting _apply_replacements_to_html with final_html (first 100 chars): {final_html[:100]}")

    # A simple validation to check if placeholders were injected
    if "{{" not in final_html:
        logger.warning("No placeholders were injected. The document might not be a good candidate for templating.")

    return final_html

# --- Public Orchestrator Function ---

def create_template_from_docx(file_stream: IO[bytes], filename: str) -> str:
    """
    Orchestrates the creation of a Liquid HTML template from a DOCX file.
    This process is optimized with a caching layer to avoid redundant API calls.
    """
    logger.info(f"[create_template_from_docx] Orchestrating template creation for '{filename}'.")
    logger.debug(f"Entering create_template_from_docx with filename: {filename}")

    # Step 1: Calculate the file's hash and check the cache
    file_hash = _get_file_hash(file_stream)
    logger.info(f"Calculated SHA-256 hash for '{filename}': {file_hash}")

    raw_html = _get_cached_html(file_hash)

    if raw_html:
        logger.info(f"Cache hit for hash '{file_hash}'. Skipping Convertio.")
    else:
        logger.info(f"Cache miss for hash '{file_hash}'. Proceeding with Convertio conversion.")
        # Step 2: If not cached, convert DOCX to raw HTML using Convertio
        conversion_id = _start_conversion(file_stream, filename)
        html_url = _poll_conversion_status(conversion_id)
        raw_html = _download_html_content(html_url)

        # Step 3: Cache the newly converted HTML
        _cache_html(file_hash, raw_html)
        logger.info(f"Successfully cached new HTML for hash '{file_hash}'.")

    # Step 4: Get a replacement map from the LLM
    replacement_map = _get_replacement_map_from_llm(raw_html)

    # Step 5: Apply the replacements to the original HTML
    templated_html = _apply_replacements_to_html(raw_html, replacement_map)

    # Step 6: Validate the final Liquid syntax
    _validate_liquid_template(templated_html)

    logger.debug("Exiting create_template_from_docx")
    return templated_html

def _validate_liquid_template(template_string: str):
    """
    Validates the Liquid syntax of the given template string.
    Raises a ValueError if the syntax is invalid.
    """
    logger.debug("Entering _validate_liquid_template")
    try:
        logger.info("Validating final Liquid template syntax.")
        Liquid(template_string)
        logger.info("Liquid template syntax is valid.")
    except Exception as e:
        logger.error(f"Liquid template validation failed: {e}", exc_info=True)
        raise ValueError("The generated template has invalid Liquid syntax.")
    logger.debug("Exiting _validate_liquid_template")
