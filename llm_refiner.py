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

    # --- Step 4.4: API Call (To be built here) ---
    # In the next step, we will add the code to send this prompt to the API.

    print("--- PROMPT ---")
    print(prompt)
    print("--- END PROMPT ---")

    # For now, we will return the initial data until the API call is implemented.
    return initial_extraction
