import os
import hashlib
import requests
import time
import sys
import base64
import json
import logging
import re
from typing import Dict
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
from bs4 import BeautifulSoup, NavigableString
from openai import OpenAI

# ... (other imports and functions remain the same)
# Import caching functions from the database module
from . import database
from . import ai_logic

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
    logger.info(f"Calculated hash: {file_hash}")

    cached_html = database.get_cached_html(file_hash)
    if cached_html:
        logger.info("Found pre-converted HTML in cache.")
        return cached_html

    logger.info("HTML not in cache. Converting with Convertio...")
    if not CONVERTIO_API_KEY:
        raise Exception("CONVERTIO_API_KEY is not set.")

    try:
        # Step 1: Start conversion using Base64 upload
        logger.info("Step 1/3: Starting Convertio conversion with Base64 upload...")
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
        logger.debug(f"Convertio start response: {response_json}")

        if response_json.get('error'):
             raise Exception(f"Convertio API Error on start: {response_json['error']}")

        conv_id = response_json["data"]["id"]

        # Step 2: Poll for conversion status
        logger.info("Step 2/3: Polling for conversion status...")
        while True:
            status_response = requests.get(f"https://api.convertio.co/convert/{conv_id}/status")
            status_response.raise_for_status()
            status_data = status_response.json()["data"]

            if status_data["step"] == "finish":
                html_url = status_data["output"]["url"]
                break
            elif status_data["step"] == "error":
                raise Exception(f"Convertio API error during conversion: {status_data.get('error')}")

            logger.info(f"Conversion in progress: {status_data['step']}...")
            time.sleep(2)

        # Step 3: Download the resulting HTML
        logger.info("Step 3/3: Downloading converted HTML...")
        html_response = requests.get(html_url)
        html_response.raise_for_status()
        html_content = html_response.text

        # Cache the new HTML
        database.cache_html(file_hash, html_content)
        logger.info("Saved new HTML to cache.")

        return html_content

    except requests.exceptions.RequestException as e:
        logger.error(f"An error occurred during Convertio API request: {e}", exc_info=True)
        if e.response is not None:
            logger.error(f"Response Status Code: {e.response.status_code}")
            logger.error(f"Response Body: {e.response.text}")
        raise e
    except Exception as e:
        logger.error(f"An unexpected error occurred in convert_docx_to_html_and_cache: {e}", exc_info=True)
        raise e


def _get_ai_replacement_map(text_map: Dict[str, str]) -> Dict[str, str]:
    """
    Generates a map of ID-to-Liquid-placeholders using a simplified text map.
    The AI's job is now much easier as the text has been pre-processed.
    """
    logger.info("Starting AI placeholder mapping workflow...")

    prompt = ai_logic.build_prompt(text_map)

    logger.info("Calling OpenAI API with pre-processed text nodes...")
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.0
    )

    response_content = response.choices[0].message.content
    logger.debug(f"GPT-4o response: {response_content}")

    try:
        return json.loads(response_content)
    except json.JSONDecodeError:
        logger.error("Failed to decode JSON from AI response.", exc_info=True)
        raise Exception("Failed to decode JSON from AI response.")


def _surgical_split_preprocessor(soup: BeautifulSoup) -> BeautifulSoup:
    """
    Finds text nodes with multiple pieces of information and surgically splits
    them into multiple, simpler nodes. This preserves styling and fixes the
    root cause of AI confusion.
    """
    logger.info("Surgically splitting complex text nodes...")

    # Regex for lines like "Label: Value"
    split_regex = re.compile(r"^\s*([a-zA-Z\s&/]+?)\s*:\s*(.*)")

    for text_node in list(soup.find_all(string=True)):
        if not text_node.strip() or text_node.parent.name in ['style', 'script']:
            continue

        original_text = str(text_node)

        # Split "Label: Value" lines
        match = split_regex.match(original_text)
        if match:
            label, value = match.groups()
            if value.strip():
                # Create a new span for the label and one for the value
                label_span = soup.new_tag("span")
                label_span.string = f"{label.strip()}: "

                value_span = soup.new_tag("span")
                value_span.string = value.strip()

                # Replace the original text node with the new spans
                text_node.replace_with(label_span)
                label_span.insert_after(value_span)
                logger.debug(f"Split line: '{original_text}'")

    return soup


def inject_liquid_placeholders(html_content: str) -> str:
    """
    Uses a surgical pre-processing step to simplify the HTML before calling the AI.
    """
    if not OPENAI_API_KEY:
        raise Exception("OPENAI_API_KEY is not set.")

    logger.info("Parsing HTML and preparing for AI injection...")
    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Surgically split complex nodes to simplify the AI's task
    soup = _surgical_split_preprocessor(soup)

    # 2. Build a map of the simplified text nodes
    id_to_text_map = {}
    node_counter = 0
    for text_node in soup.find_all(string=True):
        text = text_node.strip()
        if text and text_node.parent.name not in ['style', 'script']:
            node_id = f"liquid-node-{node_counter}"
            id_to_text_map[node_id] = text
            # We need a new way to tag elements if we replace text nodes
            # Let's wrap the text node in a span with the ID
            wrapper_span = soup.new_tag("span", attrs={"data-liquid-id": node_id})
            text_node.wrap(wrapper_span)
            node_counter += 1

    if not id_to_text_map:
        logger.warning("No text nodes found to process.")
        return str(soup)

    # 3. Get the replacement map from the AI
    id_to_liquid_map = _get_ai_replacement_map(id_to_text_map)

    # 4. Replace content by finding the wrapper spans
    logger.info("Replacing content with Liquid placeholders...")
    for node_id, liquid_variable in id_to_liquid_map.items():
        wrapper_span = soup.find("span", attrs={"data-liquid-id": node_id})
        if wrapper_span:
            # Replace the wrapper span with just the liquid variable text node
            wrapper_span.replace_with(NavigableString(liquid_variable))

    return str(soup)


def create_and_inject_from_docx(file_content: bytes) -> str:
    """
    Orchestrates the entire template creation process from a DOCX file.
    1. Converts DOCX to HTML (using cache if available).
    2. Injects Liquid placeholders into the HTML.
    Returns the final Liquid template as a string.
    """
    logger.info("Starting full template creation workflow...")

    # Step 1: Convert DOCX to HTML
    html_content = convert_docx_to_html_and_cache(file_content)
    if not html_content:
        raise Exception("Failed to get HTML content from DOCX.")

    # Step 2: Inject Liquid placeholders
    final_template = inject_liquid_placeholders(html_content)
    if not final_template:
        raise Exception("Failed to inject Liquid placeholders.")

    logger.info("Full template creation workflow completed successfully.")
    return final_template
