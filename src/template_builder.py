import os
import hashlib
import requests
import time
import sys
import base64
import json
import logging
import re
from typing import Optional, Dict
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

# --- Debugging: Log the loaded API key securely ---
if OPENAI_API_KEY:
    logger.info(f"Loaded OpenAI API Key ending with: ...{OPENAI_API_KEY[-4:]}")
else:
    logger.warning("OPENAI_API_KEY environment variable not found or is empty.")
# -------------------------------------------------
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


def _get_ai_replacement_map(id_to_text_map: Dict[str, str]) -> Dict[str, str]:
    """
    Generates a map of ID-to-Liquid-placeholders using the new GPT-5 workflow.
    """
    logger.info("Starting AI placeholder mapping workflow...")

    # 1. Annotate the text map using local regex-based classification
    logger.info("Step 1/3: Annotating text map with regex classifiers...")
    annotations = ai_logic.annotate_map(id_to_text_map)
    logger.debug(f"Generated annotations: {json.dumps(annotations, ensure_ascii=False, indent=2)}")

    # 2. Build the detailed prompt for the new model
    logger.info("Step 2/3: Building prompt for GPT-5...")
    prompt = ai_logic.build_prompt(id_to_text_map, annotations)
    logger.debug(f"Generated prompt: {prompt}")

    # 3. Call the new model
    logger.info("Step 3/3: Calling GPT-5 API to get placeholder map...")
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-5",  # Switched to the new model
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    response_content = response.choices[0].message.content
    logger.debug(f"GPT-5 response: {response_content}")

    try:
        return json.loads(response_content)
    except json.JSONDecodeError:
        logger.error("Failed to decode JSON from AI response.", exc_info=True)
        raise Exception("Failed to decode JSON from AI response.")


def _prerender_complex_nodes(soup: BeautifulSoup) -> BeautifulSoup:
    """
    Finds and directly replaces or splits complex text nodes to simplify the AI's task.
    This is a robust, deterministic solution to issues the AI struggles with.
    """
    logger.info("Pre-processing/rendering complex nodes with programmatic logic...")

    # Define regex patterns
    initials_regex = re.compile(r"^\s*[A-Z]{2,3}\s*$")
    mission_regex = re.compile(r"^\s*Mission\s+au\s+sein\s+de\s+(.*)", re.I)
    header_regex = re.compile(r"(\d+\s+ans\s+d['’]expérience)\s*(.*)")
    # This general skills regex will handle "Langues : ..." as well as others
    skills_regex = re.compile(r"^\s*([a-zA-Z\s&/]+?)\s*:\s*(.*)")

    for text_node in list(soup.find_all(string=True)):
        if not text_node.strip() or isinstance(text_node.parent, (BeautifulSoup, NavigableString)) or text_node.parent.name in ['style', 'script']:
            continue

        original_text = str(text_node).strip()

        # 1. Replace Initials (full replacement)
        if initials_regex.match(original_text):
            new_tag = soup.new_tag("span")
            new_tag.string = "{{ candidate.initials }}"
            text_node.replace_with(new_tag)
            logger.debug(f"Pre-rendered initials for: '{original_text}'")
            continue

        # 2. Replace Mission line (full replacement)
        mission_match = mission_regex.match(original_text)
        if mission_match:
            new_tag = soup.new_tag("span")
            new_tag.string = "Mission au sein de {{ experience[0].company }}"
            text_node.replace_with(new_tag)
            logger.debug(f"Pre-rendered mission line: '{original_text}'")
            continue

        # 3. Split header line
        header_match = header_regex.match(original_text)
        if header_match:
            experience_part, other_part = header_match.groups()
            if other_part.strip(): # Only split if there is other text
                experience_tag = soup.new_tag("span")
                experience_tag.string = experience_part.strip()

                other_tag = soup.new_tag("span")
                other_tag.string = other_part.strip()

                text_node.replace_with(experience_tag)
                experience_tag.insert_after(other_tag)
                logger.debug(f"Split header line: '{original_text}'")
                continue

        # 4. Split all skills lines (e.g., "Label : Value") into two separate nodes
        skills_match = skills_regex.match(original_text)
        if skills_match:
            label, value = skills_match.groups()
            if value.strip():
                label_tag = soup.new_tag("span")
                label_tag.string = f"{label.strip()} :"

                value_tag = soup.new_tag("span")
                value_tag.string = value.strip()

                text_node.replace_with(label_tag)
                label_tag.insert_after(value_tag)
                logger.debug(f"Split skills line: '{original_text}'")
                continue

    return soup


def inject_liquid_placeholders(html_content: str) -> str:
    """
    Uses a token-efficient, ID-based hybrid approach to inject Liquid placeholders.
    """
    if not OPENAI_API_KEY:
        raise Exception("OPENAI_API_KEY is not set.")

    logger.info("Parsing HTML and preparing for AI injection...")
    soup = BeautifulSoup(html_content, "html.parser")

    # --- NEW: Pre-render complex nodes to handle them programmatically ---
    soup = _prerender_complex_nodes(soup)
    # -------------------------------------------------------------------

    # 1. Add unique IDs to all REMAINING text nodes and create an ID-to-text map
    id_to_text_map = {}
    node_counter = 0
    for text_node in soup.find_all(string=True):
        if text_node.strip() and not isinstance(text_node.parent, (BeautifulSoup, NavigableString)) and text_node.parent.name not in ['style', 'script']:
            node_id = f"liquid-node-{node_counter}"
            id_to_text_map[node_id] = text_node.strip()
            text_node.parent[f"data-liquid-id"] = node_id
            node_counter += 1

    if not id_to_text_map:
        logger.warning("No text nodes found to process in inject_liquid_placeholders.")
        return str(soup)

    # 2. Get the replacement map from the AI
    id_to_liquid_map = _get_ai_replacement_map(id_to_text_map)

    # 3. Replace content and remove IDs
    logger.info("Replacing content with Liquid placeholders...")
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
