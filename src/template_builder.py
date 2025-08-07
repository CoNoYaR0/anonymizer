import os
import hashlib
import requests
import time
from typing import Optional
from dotenv import load_dotenv

# Import caching functions from the database module
from . import database

# Load environment variables
load_dotenv()
CONVERTIO_API_KEY = os.getenv("CONVERTIO_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def _calculate_file_hash(file_content: bytes) -> str:
    """
    Calculates the SHA-256 hash of the file content.
    """
    sha256_hash = hashlib.sha256()
    sha256_hash.update(file_content)
    return sha256_hash.hexdigest()


def _convert_docx_to_html(file_content: bytes) -> str:
    """
    Converts DOCX file content to HTML using the Convertio API.

    Args:
        file_content: The binary content of the DOCX file.

    Returns:
        The converted HTML content as a string.

    Raises:
        Exception: If the Convertio API key is missing or the conversion fails.
    """
    if not CONVERTIO_API_KEY:
        raise Exception("CONVERTIO_API_KEY is not set.")

    # Step 1: Start a new conversion
    start_response = requests.post(
        "https://api.convertio.co/convert",
        json={"apikey": CONVERTIO_API_KEY, "input": "upload", "outputformat": "html"}
    )
    start_response.raise_for_status()
    conv_data = start_response.json()["data"]
    conv_id = conv_data["id"]
    upload_url = conv_data["upload_url"]

    # Step 2: Upload the file content
    with open("temp_for_convertio.docx", "wb") as f:
        f.write(file_content)

    with open("temp_for_convertio.docx", "rb") as f:
        upload_response = requests.put(upload_url, data=f)

    os.remove("temp_for_convertio.docx")
    upload_response.raise_for_status()

    # Step 3: Poll for conversion status
    while True:
        status_response = requests.get(f"https://api.convertio.co/convert/{conv_id}/status")
        status_response.raise_for_status()
        status_data = status_response.json()["data"]

        if status_data["step"] == "finish":
            html_url = status_data["output"]["url"]
            break
        elif status_data["step"] == "error":
            raise Exception(f"Convertio API error: {status_data['step_percent']} - {status_data.get('error')}")

        print(f"Conversion in progress: {status_data['step']} ({status_data['step_percent']}%)")
        time.sleep(2) # Wait 2 seconds before polling again

    # Step 4: Download the resulting HTML
    html_response = requests.get(html_url)
    html_response.raise_for_status()

    return html_response.text


def _inject_liquid_placeholders(html_content: str) -> str:
    """
    Uses an LLM to intelligently replace static text in HTML with Liquid placeholders.
    """
    if not OPENAI_API_KEY:
        raise Exception("OPENAI_API_KEY is not set.")

    # TODO: Implement the LLM processing logic.
    print("TODO: Calling OpenAI API to inject Liquid placeholders.")
    return html_content.replace("Placeholder HTML", "<h1>{{ document_title }}</h1>")


def create_template_from_docx(file_name: str, file_content: bytes) -> str:
    """
    Orchestrates the full workflow for creating a template from a DOCX file.
    """
    file_hash = _calculate_file_hash(file_content)
    print(f"Calculated hash for {file_name}: {file_hash}")

    cached_html = database.get_cached_html(file_hash)
    if cached_html:
        print("Found pre-converted HTML in cache.")
        html_content = cached_html
    else:
        print("HTML not in cache. Converting with Convertio...")
        html_content = _convert_docx_to_html(file_content)
        database.cache_html(file_hash, html_content)
        print("Saved new HTML to cache.")

    print("Injecting Liquid placeholders...")
    liquid_template = _inject_liquid_placeholders(html_content)

    print("Template creation process complete.")
    return liquid_template
