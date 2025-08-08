import os
import hashlib
import requests
import time
import sys
import base64
import json
from typing import Optional, Dict
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


def _get_ai_replacement_map(id_to_text_map: Dict[str, str]) -> Dict[str, str]:
    """Sends the ID-to-text map to the AI and gets back an ID-to-Liquid map."""
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
    You are a templating expert. Your task is to analyze the following JSON object, which maps unique IDs to text content from an HTML document.
    Create a new JSON object that maps the same IDs to appropriate Liquid placeholders for any text that appears to be dynamic data (names, dates, job titles, etc.).

    Guidelines:
    - If a text value is dynamic, create a logical Liquid variable for it (e.g., "{{{{ candidate.name }}}}", "{{{{ experience.title }}}}").
    - If a text value appears to be a static label (e.g., "Experience", "Education"), **exclude its ID** from the final JSON object.
    - The keys in the returned JSON must be the original IDs.
    - Ensure the output is ONLY a valid JSON object.

    Here is the ID-to-text map to analyze:
    {json.dumps(id_to_text_map, indent=2)}

    Return the JSON object mapping IDs to Liquid placeholders now.
    """

    print("Calling OpenAI API to get placeholder map...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    response_content = response.choices[0].message.content
    print(f"DEBUG: OpenAI response: {response_content}")

    try:
        return json.loads(response_content)
    except json.JSONDecodeError:
        raise Exception("Failed to decode JSON from OpenAI response.")


def inject_liquid_placeholders(html_content: str) -> str:
    """
    Uses a token-efficient, ID-based hybrid approach to inject Liquid placeholders.
    """
    if not OPENAI_API_KEY:
        raise Exception("OPENAI_API_KEY is not set.")

    print("Parsing HTML and preparing for AI injection...")
    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Add unique IDs to all text nodes and create an ID-to-text map
    id_to_text_map = {}
    node_counter = 0
    for text_node in soup.find_all(string=True):
        if text_node.strip() and not isinstance(text_node.parent, (BeautifulSoup, NavigableString)) and text_node.parent.name not in ['style', 'script']:
            node_id = f"liquid-node-{node_counter}"
            id_to_text_map[node_id] = text_node.strip()
            text_node.parent[f"data-liquid-id"] = node_id
            node_counter += 1

    if not id_to_text_map:
        print("No text nodes found to process.")
        return str(soup)

    # 2. Get the replacement map from the AI
    id_to_liquid_map = _get_ai_replacement_map(id_to_text_map)

    # 3. Replace content and remove IDs
    print("Replacing content with Liquid placeholders...")
    for node_id, liquid_variable in id_to_liquid_map.items():
        element = soup.find(attrs={f"data-liquid-id": node_id})
        if element:
            # Clear the element and add the new Liquid variable
            element.clear()
            element.append(NavigableString(liquid_variable))

    # 4. Clean up all the data-liquid-id attributes
    for element in soup.find_all(attrs={"data-liquid-id": True}):
        del element["data-liquid-id"]

    return str(soup)


def create_and_inject_from_docx(file_content: bytes) -> str:
    """
    Orchestrates the entire template creation process from a DOCX file.
    1. Converts DOCX to HTML (using cache if available).
    2. Injects Liquid placeholders into the HTML.
    Returns the final Liquid template as a string.
    """
    print("Starting full template creation workflow...")

    # Step 1: Convert DOCX to HTML
    html_content = convert_docx_to_html_and_cache(file_content)
    if not html_content:
        raise Exception("Failed to get HTML content from DOCX.")

    # Step 2: Inject Liquid placeholders
    final_template = inject_liquid_placeholders(html_content)
    if not final_template:
        raise Exception("Failed to inject Liquid placeholders.")

    print("Full template creation workflow completed successfully.")
    return final_template
