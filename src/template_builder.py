import os
import hashlib
import requests
import time
import sys
from typing import Optional
from dotenv import load_dotenv

# Import caching functions from the database module
from . import database

# Load environment variables
load_dotenv()
CONVERTIO_API_KEY = os.getenv("CONVERTIO_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def _calculate_file_hash(file_content: bytes) -> str:
    """Calculates the SHA-256 hash of the file content."""
    sha256_hash = hashlib.sha256()
    sha256_hash.update(file_content)
    return sha256_hash.hexdigest()

def convert_docx_to_html_and_cache(file_content: bytes) -> str:
    """
    Checks cache for HTML. If not found, converts DOCX to HTML via Convertio and caches it.
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

    try:
        # Step 1: Start a new conversion
        print("Step 1/4: Starting Convertio conversion...")
        start_response = requests.post(
            "https://api.convertio.co/convert",
            json={"apikey": CONVERTIO_API_KEY, "input": "upload", "outputformat": "html"}
        )
        start_response.raise_for_status()
        response_json = start_response.json()
        print(f"DEBUG: Convertio start response: {response_json}") # DEBUG LOGGING
        conv_data = response_json["data"]
        conv_id = conv_data["id"]
        upload_url = conv_data["upload_url"]

        # Step 2: Upload the file content
        print("Step 2/4: Uploading file to Convertio...")
        with open("temp_for_convertio.docx", "wb") as f:
            f.write(file_content)

        with open("temp_for_convertio.docx", "rb") as f:
            upload_response = requests.put(upload_url, data=f)

        os.remove("temp_for_convertio.docx")
        upload_response.raise_for_status()

        # Step 3: Poll for conversion status
        print("Step 3/4: Polling for conversion status...")
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

        # Step 4: Download the resulting HTML
        print("Step 4/4: Downloading converted HTML...")
        html_response = requests.get(html_url)
        html_response.raise_for_status()
        html_content = html_response.text

        # Cache the new HTML
        database.cache_html(file_hash, html_content)
        print("Saved new HTML to cache.")

        return html_content

    except requests.exceptions.RequestException as e:
        # This will catch any network-related errors and print the response from Convertio
        print(f"FATAL: An error occurred during Convertio API request: {e}", file=sys.stderr)
        if e.response is not None:
            print(f"Response Status Code: {e.response.status_code}", file=sys.stderr)
            print(f"Response Body: {e.response.text}", file=sys.stderr)
        raise e
    except Exception as e:
        print(f"FATAL: An unexpected error occurred in convert_docx_to_html_and_cache: {e}", file=sys.stderr)
        raise e

def inject_liquid_placeholders(html_content: str) -> str:
    """
    Uses an LLM to intelligently replace static text in HTML with Liquid placeholders.
    """
    # ... (rest of the function remains the same)
    if not OPENAI_API_KEY:
        raise Exception("OPENAI_API_KEY is not set.")
    print("TODO: Calling OpenAI API to inject Liquid placeholders.")
    injected_html = html_content + "\n<!-- Injected by AI with Liquid placeholders -->"
    return injected_html.replace("<p>This is content from a DOCX.</p>", "<p>{{ placeholder_text }}</p>")
