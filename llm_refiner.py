import os
import httpx
import json

# --- Configuration ---
# The endpoint for the specific model we want to use from the Hugging Face Inference API.
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
# Get the API key from the environment variables.
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

def refine_extraction_with_llm(raw_text: str, initial_extraction: dict) -> dict:
    """
    Uses a Large Language Model to refine the initial data extraction.

    Args:
        raw_text: The raw text extracted from the OCR process.
        initial_extraction: A dictionary with the initial entities extracted by spaCy.

    Returns:
        A dictionary with the refined and structured data.
    """
    if not HUGGINGFACE_API_KEY:
        print("Warning: HUGGINGFACE_API_KEY not found. Skipping LLM refinement.")
        # Return the initial data if the LLM is not configured
        return initial_extraction

    # --- Step 4.3: Prompt Engineering ---
    # We construct a detailed prompt with a clear role, instructions, and a schema for the output.
    # The [INST] and [/INST] tokens are specific to Mistral's instruction-tuned models.

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
  "persons": ["string"],
  "locations": ["string"],
  "emails": ["string"],
  "phones": ["string"],
  "skills": [
    {{
      "category": "string",
      "skills_list": ["string"]
    }}
  ],
  "experience": [
    {{
      "job_title": "string",
      "company_name": "string",
      "start_date": "string",
      "end_date": "string",
      "job_context": "string",
      "missions": ["string"],
      "technologies": ["string"]
    }}
  ]
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

    # --- Step 4.4: API Call ---
    # We send the request to the Hugging Face Inference API.
    # We use a timeout to handle cases where the API might be slow to respond.
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(API_URL, headers=headers, json={"inputs": prompt})

        if response.status_code != 200:
            print(f"Error from Hugging Face API: {response.status_code} - {response.text}")
            return initial_extraction # Fallback to the initial data

        # The response from the LLM is a list containing a dictionary.
        llm_output = response.json()[0]['generated_text']

        # The prompt instructs the LLM to only return the JSON, but sometimes it might
        # still include the prompt itself. We need to find the start of the JSON.
        json_start_index = llm_output.find('{')
        if json_start_index == -1:
            print("Error: LLM did not return a valid JSON object.")
            return initial_extraction

        # Extract and parse the JSON part of the response
        json_string = llm_output[json_start_index:]
        refined_data = json.loads(json_string)

        return refined_data

    except httpx.RequestError as e:
        print(f"Error making request to Hugging Face API: {e}")
        return initial_extraction # Fallback to the initial data
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from LLM response: {e}")
        print(f"Raw LLM output was: {llm_output}")
        return initial_extraction # Fallback
