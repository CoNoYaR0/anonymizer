import os
import hashlib
import requests
import time
import sys
import base64
import json
from typing import Optional, List
from dotenv import load_dotenv
from bs4 import BeautifulSoup, NavigableString
from openai import OpenAI

# ... (other imports and functions remain the same)
# Import caching functions from the database module
from . import database

# Load environment variables
load_dotenv()
CONVERTIO_API_KEY = os.getenv("CONVERTIO_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# ... (_calculate_file_hash and convert_docx_to_html_and_cache are unchanged)
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
        # Step 1: Start conversion using Base64 upload
        print("Step 1/3: Starting Convertio conversion with Base64 upload...")
        encoded_file = base64.b64encode(file_content).decode('ascii')

        start_response = requests.post(
            "https://api.convertio.co/convert",
            json={
                "apikey": CONVERTIO_API_KEY,
                "input": "base64",
                "file": encoded_file,
                "filename": "template.docx",
                "outputformat": "html"
            }
        )
        start_response.raise_for_status()
        response_json = start_response.json()
        print(f"DEBUG: Convertio start response: {response_json}")

        if response_json.get('error'):
             raise Exception(f"Convertio API Error on start: {response_json['error']}")

        conv_id = response_json["data"]["id"]

        # Step 2: Poll for conversion status
        print("Step 2/3: Polling for conversion status...")
        while True:
            status_response = requests.get(f"https://api.convertio.co/convert/{conv_id}/status")
            status_response.raise_for_status()
            status_data = status_response.json()["data"]

            if status_data["step"] == "finish":
                html_url = status_data["output"]["url"]
                break
            elif status_data["step"] == "error":
                raise Exception(f"Convertio API error during conversion: {status_data.get('error')}")

            print(f"Conversion in progress: {status_data['step']}...")
            time.sleep(2)

        # Step 3: Download the resulting HTML
        print("Step 3/3: Downloading converted HTML...")
        html_response = requests.get(html_url)
        html_response.raise_for_status()
        html_content = html_response.text

        # Cache the new HTML
        database.cache_html(file_hash, html_content)
        print("Saved new HTML to cache.")

        return html_content

    except requests.exceptions.RequestException as e:
        print(f"FATAL: An error occurred during Convertio API request: {e}", file=sys.stderr)
        if e.response is not None:
            print(f"Response Status Code: {e.response.status_code}", file=sys.stderr)
            print(f"Response Body: {e.response.text}", file=sys.stderr)
        raise e
    except Exception as e:
        print(f"FATAL: An unexpected error occurred in convert_docx_to_html_and_cache: {e}", file=sys.stderr)
        raise e

def _create_text_chunks(text_nodes: List[str], max_chars: int = 15000) -> List[List[str]]:
    """Groups a list of text strings into chunks below a max character limit."""
    chunks = []
    current_chunk = []
    current_length = 0
    for text in text_nodes:
        if current_length + len(text) > max_chars:
            chunks.append(current_chunk)
            current_chunk = []
            current_length = 0
        current_chunk.append(text)
        current_length += len(text)
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def inject_liquid_placeholders(html_content: str) -> str:
    """
    Uses an LLM to intelligently replace static text in HTML with Liquid placeholders.
    Handles large documents by chunking the text sent to the API.
    """
    if not OPENAI_API_KEY:
        raise Exception("OPENAI_API_KEY is not set.")

    print("Parsing HTML with BeautifulSoup...")
    soup = BeautifulSoup(html_content, "html.parser")

    text_nodes = [text for text in soup.find_all(string=True) if text.strip()]
    text_chunks = _create_text_chunks(text_nodes)

    client = OpenAI(api_key=OPENAI_API_KEY)
    full_replacement_map = {}

    print(f"Processing {len(text_chunks)} chunks for OpenAI API...")
    for i, chunk in enumerate(text_chunks):
        print(f"Processing chunk {i+1}/{len(text_chunks)}...")
        prompt = f"""
        You are a templating expert. Your task is to analyze the following text content and convert it into a valid JSON object that maps original text to a Liquid placeholder.
        Guidelines:
        - Identify dynamic data (names, dates, job titles, etc.).
        - Map this dynamic text to a logical Liquid variable (e.g., "{{{{ candidate.name }}}}").
        - Do NOT include static labels (e.g., "Experience", "Education") in the JSON.
        - The JSON keys must be the EXACT original text.
        - Ensure the output is ONLY a valid JSON object.
        Text to analyze:
        {json.dumps(chunk, indent=2)}
        Return the JSON object now.
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        response_content = response.choices[0].message.content

        try:
            chunk_map = json.loads(response_content)
            full_replacement_map.update(chunk_map)
        except json.JSONDecodeError:
            print(f"Warning: Failed to decode JSON from chunk {i+1}. Skipping.", file=sys.stderr)
            continue

        # Add a delay to avoid hitting the TPM rate limit
        if i < len(text_chunks) - 1:
            print("Waiting for 2 seconds to respect rate limits...")
            time.sleep(2)

    print("Replacing text nodes with Liquid placeholders...")
    for text_node in soup.find_all(string=True):
        if text_node.strip() in full_replacement_map:
            new_content = full_replacement_map[text_node.strip()]
            text_node.replace_with(NavigableString(new_content))

    return str(soup)
