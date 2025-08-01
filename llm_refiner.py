import os
import httpx
import json
import logging
import re

# Get a logger for the current module
logger = logging.getLogger(__name__)

def clean_for_bart(text: str) -> str:
    """
    Sanitizes text to be a single, clean block of natural language
    for the BART model.
    """
    # Replace various newline characters with a single space
    text = text.replace('\n', ' ').replace('\r', ' ')
    # Replace multiple whitespace characters with a single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# --- Configuration ---
API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

def refine_extraction_with_llm(raw_text: str, initial_extraction: dict) -> tuple[bool, dict]:
    """
    Uses a Large Language Model to refine initial data extraction.
    Note: Currently uses bart-large-cnn, a summarization model, as a stable placeholder.
    """
    if not HUGGINGFACE_API_KEY:
        logger.warning("HUGGINGFACE_API_KEY not found. Skipping LLM refinement.")
        return True, initial_extraction  # Not a failure, but a skip.

    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

    logger.info("Cleaning and truncating text for BART model...")
    # Clean the raw text to be more natural language like.
    cleaned_text = clean_for_bart(raw_text)

    # Truncate to ~700 words to stay within model limits.
    words = cleaned_text.split()
    truncated_text = " ".join(words[:700])

    logger.debug(f"Cleaned and truncated text: {truncated_text[:200]}...") # Log a preview

    # The payload for BART is just the clean text.
    payload = {"inputs": truncated_text}

    logger.info(f"Calling Hugging Face Inference API ({API_URL}) with sanitized payload...")
    logger.debug(f"API URL: {API_URL}")
    logger.debug(f"Headers: {{'Authorization': 'Bearer [REDACTED]'}}") # Avoid logging the key
    logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(API_URL, headers=headers, json=payload)

        if response.status_code != 200:
            error_detail = {
                "error": "Hugging Face API Error",
                "status_code": response.status_code,
                "response_text": response.text
            }
            logger.error(f"Hugging Face API returned non-200 status: {response.status_code} - {response.text}")
            return False, error_detail

        # The output from BART is a summary string, not a JSON object.
        summary_text = response.json()[0]['summary_text']
        logger.info(f"Successfully received summary from BART: {summary_text[:100]}...")

        # We are not replacing the initial extraction, but augmenting it.
        # The downstream process expects a dictionary in the original format.
        final_data = initial_extraction.copy()

        # Add the summary as a new key.
        final_data['llm_summary'] = summary_text

        return True, final_data

    except httpx.RequestError as e:
        error_detail = {"error": "HTTPX Request Error", "details": str(e)}
        logger.error(f"Error making request to Hugging Face API: {e}")
        return False, error_detail
    except json.JSONDecodeError as e:
        error_detail = {"error": "JSON Decode Error", "details": str(e), "llm_output": llm_output}
        logger.error(f"Error decoding JSON from LLM response: {e}. Raw output: {llm_output}")
        return False, error_detail
    except Exception as e:
        error_detail = {"error": "An unexpected error occurred", "details": str(e)}
        logger.critical(f"An unexpected error in LLM refiner: {e}", exc_info=True)
        return False, error_detail
