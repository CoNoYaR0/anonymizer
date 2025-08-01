import os
import httpx
import json
import logging

# Get a logger for the current module
logger = logging.getLogger(__name__)

# --- Configuration ---
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

def refine_extraction_with_llm(raw_text: str, initial_extraction: dict) -> tuple[bool, dict]:
    """
    Uses a Large Language Model to refine initial data extraction.

    Args:
        raw_text: Raw text from OCR.
        initial_extraction: Dictionary from the initial spaCy extraction.

    Returns:
        A tuple containing:
        - bool: True if successful, False otherwise.
        - dict: The refined data or an error dictionary.
    """
    if not HUGGINGFACE_API_KEY:
        logger.warning("HUGGINGFACE_API_KEY not found. Skipping LLM refinement.")
        return True, initial_extraction  # Not a failure, but a skip.

    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    initial_extraction_json = json.dumps(initial_extraction, indent=2)

    prompt = f"""
[INST]
You are a highly intelligent and precise data extraction bot. Your sole purpose is to extract information from a CV's raw text and format it as a perfect, machine-readable JSON object.
**Instructions:**
1.  You will be given raw text that was extracted from a PDF using an OCR tool. This text may contain errors.
2.  You will also be given a preliminary JSON object that contains a "first pass" extraction of some entities.
3.  Your task is to **correct and complete** this JSON object.
4.  Use the raw text to correct any spelling mistakes or OCR errors in the preliminary JSON.
5.  Carefully parse the raw text to extract the professional experiences and skills. Pay close attention to dates, job titles, and lists of technologies.
6.  **The final output MUST be ONLY the JSON object.** Do not include any other text, explanations, or apologies. Do not use markdown formatting like ```json.
**JSON Schema to Follow:**
Your final JSON output must follow this exact structure:
{{
  "persons": ["string"], "locations": ["string"], "emails": ["string"], "phones": ["string"],
  "skills": [{{ "category": "string", "skills_list": ["string"] }}],
  "experience": [{{ "job_title": "string", "company_name": "string", "start_date": "string", "end_date": "string", "job_context": "string", "missions": ["string"], "technologies": ["string"] }}]
}}
**Input Data:**
**Raw OCR Text:**
```
{raw_text}
```
**Preliminary JSON:**
```json
{initial_extraction_json}
```
[/INST]
"""
    payload = {"inputs": prompt}

    logger.info("Calling Hugging Face Inference API for refinement...")
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
