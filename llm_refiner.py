import os
import json
import logging
from openai import OpenAI, RateLimitError, APIError

# --- Configuration ---
logger = logging.getLogger(__name__)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize the OpenAI client
# It will automatically pick up the OPENAI_API_KEY from the environment.
if OPENAI_API_KEY:
    client = OpenAI()
else:
    client = None

def refine_extraction_with_llm(raw_text: str, initial_extraction: dict) -> tuple[bool, dict]:
    """
    Uses OpenAI's GPT-4o to refine and complete the initial data extraction.

    Args:
        raw_text: Raw text extracted from the OCR process.
        initial_extraction: A dictionary with the initial entities from spaCy.

    Returns:
        A tuple containing:
        - bool: True if successful, False otherwise.
        - dict: The refined JSON data or an error dictionary.
    """
    if not client:
        logger.warning("OPENAI_API_KEY not found. Skipping LLM refinement.")
        return True, initial_extraction

    initial_extraction_json = json.dumps(initial_extraction, indent=2, ensure_ascii=False)

    system_prompt = """
You are an expert data extraction and refinement assistant. Your primary goal is to transform raw, messy OCR text from a CV into a clean, professional, and structured JSON object.

**Core Directives:**
1.  **Analyze and Extract:** Scrutinize the "Raw OCR Text" to identify all professional experiences, skills, and educational background.
2.  **Clean and Correct:**
    - Actively correct typos, spelling errors, and grammatical mistakes.
    - Remove any junk characters, symbols, or repeated patterns that are clearly OCR artifacts (e.g., "Ÿ_", "NENENEN...", "KSKKEKE", etc.).
    - Reformulate awkward sentences or phrases to improve clarity and professionalism, while preserving the original meaning.
3.  **Structure the Output:** Populate the JSON object based on the cleaned and refined data. Pay special attention to the "experience" and "skills" sections.
4.  **Enforce Schema:** The final output MUST be ONLY a valid JSON object. Do not include any explanatory text, apologies, or markdown formatting. The JSON must strictly adhere to the following schema:
{
  "persons": ["string"],
  "locations": ["string"],
  "emails": ["string"],
  "phones": ["string"],
  "skills": [
    {
      "category": "string (e.g., 'Languages', 'Databases', 'Frameworks')",
      "skills_list": ["string"]
    }
  ],
  "experience": [
    {
      "job_title": "string",
      "company_name": "string",
      "start_date": "string",
      "end_date": "string",
      "job_context": "string (A brief summary of the role)",
      "missions": ["string"],
      "technologies": ["string"]
    }
  ]
}
"""

    user_prompt = f"""
Here is the data to process:

**Raw OCR Text:**
```
{raw_text}
```

**Preliminary JSON:**
```json
{initial_extraction_json}
```
"""

    logger.info("Calling OpenAI API (gpt-4o) for refinement...")
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,  # Lower temperature for more deterministic, structured output
            response_format={"type": "json_object"}, # Enforce JSON output
        )

        llm_output = response.choices[0].message.content
        logger.info("Successfully received response from GPT-4o.")
        logger.debug(f"Raw LLM output: {llm_output}")

        # The output should be a valid JSON string already, thanks to response_format
        refined_data = json.loads(llm_output)
        return True, refined_data

    except RateLimitError as e:
        error_detail = {"error": "OpenAI Rate Limit Error", "details": str(e)}
        logger.error("OpenAI API rate limit exceeded.")
        return False, error_detail
    except APIError as e:
        error_detail = {"error": "OpenAI API Error", "status_code": e.status_code, "details": str(e)}
        logger.error(f"OpenAI API returned an error: {e.status_code} - {e.message}")
        return False, error_detail
    except json.JSONDecodeError as e:
        error_detail = {"error": "JSON Decode Error", "details": str(e), "llm_output": llm_output}
        logger.error(f"Failed to decode JSON from OpenAI response: {e}")
        return False, error_detail
    except Exception as e:
        error_detail = {"error": "An unexpected error occurred", "details": str(e)}
        logger.critical(f"An unexpected error occurred during OpenAI call: {e}", exc_info=True)
        return False, error_detail
