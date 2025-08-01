import os
import httpx
import json
import logging

# Get a logger for the current module
logger = logging.getLogger(__name__)

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

    # Since BART is a summarization model, we frame the task as summarizing the CV into a JSON object.
    # We provide the initial extraction as context to guide the summary.
    initial_extraction_json = json.dumps(initial_extraction, indent=2)

    prompt = f"""
Summarize the following CV text into a structured JSON format. Use the provided "Preliminary JSON" as a guide for the names, emails, and phones to include. Focus on extracting and structuring the work experience and skills.

CV Text:
{raw_text}

Preliminary JSON:
{initial_extraction_json}

Structured JSON Summary:
"""

    # BART expects the payload in a slightly different format for summarization
    payload = {
        "inputs": prompt,
        "parameters": {
            "do_sample": False,
            "max_length": 1024 # Increased max length for potentially long CVs
        }
    }

    logger.info(f"Calling Hugging Face Inference API ({API_URL}) for refinement...")
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

        llm_output = response.json()[0]['generated_text']
        json_start_index = llm_output.find('{')

        if json_start_index == -1:
            error_detail = {"error": "LLM did not return a valid JSON object.", "llm_output": llm_output}
            logger.error(f"LLM response did not contain a JSON object. Raw output: {llm_output}")
            return False, error_detail

        json_string = llm_output[json_start_index:]
        refined_data = json.loads(json_string)
        logger.info("Successfully refined extraction with LLM.")
        return True, refined_data

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
