import io
import os
import logging
import time
import base64
from typing import IO
import httpx
from openai import OpenAI
from liquid import Liquid

# --- Configuration ---
logger = logging.getLogger(__name__)
CONVERTIO_API_KEY = os.getenv("CONVERTIO_API_KEY", "b1ba2b0069023e1b292f3936d5c62197")
CONVERTIO_API_URL = "https://api.convertio.co/convert"

# --- Private Helper Functions ---

def _start_conversion(file_stream: IO[bytes], filename: str) -> str:
    """
    Starts a new conversion on the Convertio API using the base64 method.
    """
    if not CONVERTIO_API_KEY:
        raise ValueError("CONVERTIO_API_KEY environment variable is not set.")

    logger.info(f"Starting Convertio conversion for '{filename}'.")

    file_base64 = base64.b64encode(file_stream.read()).decode('utf-8')

    payload = {
        "apikey": CONVERTIO_API_KEY,
        "input": "base64",
        "file": file_base64,
        "filename": filename,
        "outputformat": "html"
    }

    with httpx.Client() as client:
        response = client.post(CONVERTIO_API_URL, json=payload, timeout=30)
        response.raise_for_status() # Will raise an exception for 4xx/5xx responses

        data = response.json()
        if data.get("status") == "error":
            raise ValueError(f"Convertio API error: {data.get('error')}")

        conversion_id = data.get("data", {}).get("id")
        if not conversion_id:
            raise ValueError("Failed to get a conversion ID from Convertio.")

        logger.info(f"Successfully started conversion with ID: {conversion_id}")
        return conversion_id

def _poll_conversion_status(conversion_id: str) -> str:
    """
    Polls the Convertio API for the status of a conversion until it is finished.
    Returns the URL of the output file.
    """
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
            step_percent = data.get("data", {}).get("step_percent", 0)
            logger.info(f"Conversion status: {step} ({step_percent}%)")

            if step == "finish":
                output_url = data.get("data", {}).get("output", {}).get("url")
                if not output_url:
                    raise ValueError("Conversion finished, but no output URL was provided.")
                logger.info("Conversion finished successfully.")
                return output_url
            elif step == "error":
                raise ValueError("Conversion failed at Convertio.")

            time.sleep(2) # Wait for 2 seconds before polling again

def _download_html_content(url: str) -> str:
    """
    Downloads the content from the given URL.
    """
    logger.info(f"Downloading converted HTML from: {url}")
    with httpx.Client() as client:
        response = client.get(url, timeout=60, follow_redirects=True)
        response.raise_for_status()
        return response.text

def _validate_liquid_syntax(template_string: str):
    """
    Validates the Liquid syntax of a template string.
    Raises an exception on failure.
    """
    logger.info("Validating final Liquid syntax.")
    try:
        Liquid(template_string, from_file=False)
        logger.info("Liquid syntax is valid.")
    except Exception as e:
        raise ValueError(f"Final template validation failed: {e}")

def _inject_liquid_with_llm(html_content: str) -> str:
    """
    Uses an LLM to inject Liquid placeholders into the provided HTML content.
    Includes a self-correction loop for validation.
    """
    logger.info("Starting LLM process to inject Liquid placeholders.")
    max_retries = 3
    last_error = None
    templated_html = ""
    client = OpenAI()

    system_prompt = """
You are an expert in Liquid templating. Your task is to take a fully rendered, static HTML CV and intelligently replace static personal content with dynamic Liquid template tags. Your goal is to inject Liquid placeholders in a way that makes the file reusable as a dynamic template, without breaking the structure or formatting.

🔒 RULES:
1.  **DO NOT MODIFY HTML STRUCTURE**: Preserve all HTML tags, inline styles, and layout exactly as they are.
2.  **INJECT ONLY VALID LIQUID**: All Liquid tags must be 100% syntactically valid. Every `{% for ... %}` must be matched with `{% endfor %}`.
3.  **USE STANDARD VARIABLES**: Use `{{ name }}`, `{{ title }}`, `{% for job in experiences %}`, `{{ job.title }}`, etc.
4.  **NEVER OUTPUT EXPLANATIONS**: Only output the final, fully templated HTML. No markdown, no comments.
5.  **IF RETRYING AFTER ERROR**, you MUST fix the specific syntax error provided.
"""
    user_html_prompt = f"Here is the raw HTML to be templated:\n\n```html\n{html_content}\n```"

    for attempt in range(max_retries):
        logger.info(f"Attempt {attempt + 1} of {max_retries} to inject and validate Liquid syntax.")
        feedback_prompt = ""
        if last_error:
            feedback_prompt = f"\n\n**IMPORTANT:** Your previous attempt failed with a Liquid syntax error. You MUST fix this specific issue: {last_error}"

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_html_prompt + feedback_prompt}]

        try:
            response = client.chat.completions.create(model="gpt-4o", messages=messages, temperature=0.0)
            templated_html = response.choices[0].message.content
            if templated_html.startswith("```html"):
                templated_html = templated_html[7:]
            if templated_html.endswith("```"):
                templated_html = templated_html[:-3]

            _validate_liquid_syntax(templated_html)
            logger.info("Successfully generated and validated template.")
            return templated_html.strip()
        except ValueError as e:
            logger.warning(f"Attempt {attempt + 1} failed validation. Error: {e}")
            last_error = e
        except Exception as e:
            logger.error(f"An unexpected error occurred during Liquid injection attempt {attempt + 1}: {e}", exc_info=True)
            raise ValueError(f"An unexpected error occurred during template generation: {e}")

    raise ValueError(f"Failed to create a valid template after {max_retries} attempts. Last syntax error: {last_error}")

# --- Public Orchestrator Function ---

def create_template_from_docx(file_stream: IO[bytes], filename: str) -> str:
    """
    Orchestrates the creation of a Liquid HTML template from a DOCX file.
    This process uses the Convertio API for high-fidelity DOCX-to-HTML conversion,
    and then uses an LLM to inject Liquid placeholders.
    """
    logger.info(f"[create_template_from_docx] Orchestrating template creation for '{filename}'.")

    # Step 1: Convert DOCX to raw HTML using Convertio
    conversion_id = _start_conversion(file_stream, filename)
    html_url = _poll_conversion_status(conversion_id)
    raw_html = _download_html_content(html_url)

    # Step 2: Inject Liquid placeholders with a validation and self-correction loop
    templated_html = _inject_liquid_with_llm(raw_html)

    return templated_html
