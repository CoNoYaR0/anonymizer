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

def convert_docx_to_html_and_cache(file_content: bytes) -> str:
    """
    Checks cache for HTML. If not found, converts DOCX to HTML via Convertio and caches it.

    Returns:
        The raw HTML content.
    """
    file_hash = _calculate_file_hash(file_content)
    print(f"Calculated hash: {file_hash}")

    cached_html = database.get_cached_html(file_hash)
    if cached_html:
        print("Found pre-converted HTML in cache.")
        return cached_html

    print("HTML not in cache. Converting with Convertio...")
    if not CONVERTIO_API_KEY:
        raise Exception("CONVERTIO_API_KEY is not set.")

    # Convertio API workflow
    start_response = requests.post(
        "https://api.convertio.co/convert",
        json={"apikey": CONVERTIO_API_KEY, "input": "upload", "outputformat": "html"}
    )
    start_response.raise_for_status()
    conv_data = start_response.json()["data"]
    conv_id = conv_data["id"]
    upload_url = conv_data["upload_url"]

    with open("temp_for_convertio.docx", "wb") as f:
        f.write(file_content)

    with open("temp_for_convertio.docx", "rb") as f:
        upload_response = requests.put(upload_url, data=f)

    os.remove("temp_for_convertio.docx")
    upload_response.raise_for_status()

    while True:
        status_response = requests.get(f"https://api.convertio.co/convert/{conv_id}/status")
        status_response.raise_for_status()
        status_data = status_response.json()["data"]

        if status_data["step"] == "finish":
            html_url = status_data["output"]["url"]
            break
        elif status_data["step"] == "error":
            raise Exception(f"Convertio API error: {status_data.get('error')}")

        print(f"Conversion in progress: {status_data['step']}...")
        time.sleep(2)

    html_response = requests.get(html_url)
    html_response.raise_for_status()
    html_content = html_response.text

    # Cache the new HTML
    database.cache_html(file_hash, html_content)
    print("Saved new HTML to cache.")

    return html_content

def inject_liquid_placeholders(html_content: str) -> str:
    """
    Uses an LLM to intelligently replace static text in HTML with Liquid placeholders.
    This is now a standalone function.
    """
    if not OPENAI_API_KEY:
        raise Exception("OPENAI_API_KEY is not set.")

    # TODO: Implement the real LLM processing logic using BeautifulSoup.
    print("TODO: Calling OpenAI API to inject Liquid placeholders.")

    # Placeholder logic for demonstration
    # In a real scenario, this would involve complex logic to parse and replace.
    # For now, let's just add a placeholder banner.
    injected_html = html_content + "\n<!-- Injected by AI with Liquid placeholders -->"
    return injected_html.replace("<p>This is content from a DOCX.</p>", "<p>{{ placeholder_text }}</p>")
