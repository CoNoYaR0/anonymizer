import io
import os
import logging
import time
import base64
import json
from typing import IO
import httpx
from openai import OpenAI
from liquid import Liquid
from bs4 import BeautifulSoup

# --- Configuration ---
logger = logging.getLogger(__name__)
CONVERTIO_API_KEY = os.getenv("CONVERTIO_API_KEY", "b1ba2b0069023e1b292f3936d5c62197")
CONVERTIO_API_URL = "https://api.convertio.co/convert"

# --- Private Helper Functions: Convertio Workflow ---

def _start_conversion(file_stream: IO[bytes], filename: str) -> str:
    """Starts a new conversion on the Convertio API."""
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
        if data.get("status") == "error":
            raise ValueError(f"Convertio API error: {data.get('error')}")
        conversion_id = data.get("data", {}).get("id")
        if not conversion_id:
            raise ValueError("Failed to get a conversion ID from Convertio.")
        logger.info(f"Successfully started conversion with ID: {conversion_id}")
        return conversion_id

def _poll_conversion_status(conversion_id: str) -> str:
    """Polls Convertio for conversion status and returns the output file URL."""
    logger.info(f"Polling status for conversion ID: {conversion_id}")
    status_url = f"{CONVERTIO_API_URL}/{conversion_id}/status"
    with httpx.Client() as client:
        while True:
            response = client.get(status_url, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "error":
                raise ValueError(f"Convertio status check failed: {data.get('error')}")
            step = data.get("data", {}).get("step")
            logger.info(f"Conversion status: {step} ({data.get('data', {}).get('step_percent', 0)}%)")
            if step == "finish":
                output_url = data.get("data", {}).get("output", {}).get("url")
                if not output_url:
                    raise ValueError("Conversion finished, but no output URL was provided.")
                logger.info("Conversion finished successfully.")
                return output_url
            elif step == "error":
                raise ValueError("Conversion failed at Convertio.")
            time.sleep(2)

def _download_html_content(url: str) -> str:
    """Downloads the HTML content from the given URL."""
    logger.info(f"Downloading converted HTML from: {url}")
    with httpx.Client() as client:
        response = client.get(url, timeout=60, follow_redirects=True)
        response.raise_for_status()
        return response.text

# --- Private Helper Functions: Templating Workflow ---

def _get_replacement_map_from_llm(html_content: str) -> dict:
    """
    Extracts text from HTML, sends it to an LLM, and gets back a map of
    static text to its corresponding Liquid placeholder.
    """
    logger.info("Extracting text from HTML for LLM processing.")
    soup = BeautifulSoup(html_content, 'html.parser')
    text_content = soup.get_text(separator='\n', strip=True)

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
        replacement_map = json.loads(response.choices[0].message.content)
        logger.info("Successfully received replacement map from LLM.")
        return replacement_map
    except Exception as e:
        logger.error(f"LLM replacement map generation failed: {e}", exc_info=True)
        raise ValueError("Failed to generate replacement map using the LLM.")

def _apply_replacements_to_html(html_content: str, replacement_map: dict) -> str:
    """
    Performs a safe search-and-replace on the HTML content using the provided map.
    """
    logger.info(f"Applying {len(replacement_map)} replacements to the HTML.")
    # Sort by length descending to replace longer strings first (e.g., "Software Engineer" before "Engineer")
    sorted_replacements = sorted(replacement_map.items(), key=lambda item: len(item[0]), reverse=True)

    for original_text, liquid_placeholder in sorted_replacements:
        html_content = html_content.replace(original_text, liquid_placeholder)

    # A simple validation to check if placeholders were injected
    if "{{" not in html_content:
        logger.warning("No placeholders were injected. The document might not be a good candidate for templating.")

    return html_content

# --- Public Orchestrator Function ---

def create_template_from_docx(file_stream: IO[bytes], filename: str) -> str:
    """
    Orchestrates the creation of a Liquid HTML template from a DOCX file.
    This process is optimized to avoid LLM token limits and improve reliability.
    """
    logger.info(f"[create_template_from_docx] Orchestrating template creation for '{filename}'.")

    # Step 1: Convert DOCX to raw HTML using Convertio
    conversion_id = _start_conversion(file_stream, filename)
    html_url = _poll_conversion_status(conversion_id)
    raw_html = _download_html_content(html_url)

    # Step 2: Get a replacement map from the LLM
    replacement_map = _get_replacement_map_from_llm(raw_html)

    # Step 3: Apply the replacements to the original HTML
    templated_html = _apply_replacements_to_html(raw_html, replacement_map)

    return templated_html
