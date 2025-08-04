# Agent Instructions for `cv-anonymizer-backend`

This document provides a technical overview of the project, intended for an AI software engineer (like Jules). Its purpose is to outline the architecture, data flow, and key components to facilitate efficient task completion.

## 1. Core Objective

The primary goal of this project is to create a FastAPI backend that accepts a CV (PDF), processes it through a multi-stage pipeline, and returns a link to an anonymized `.docx` version of the CV.

## 2. System Architecture & Data Flow

The application follows a sequential pipeline model. Here is the typical flow for a `/upload` request:

1.  **HTTP Request (`/upload`)**: `main.py` receives a `multipart/form-data` request containing a PDF file.
2.  **Deduplication**: The SHA256 hash of the PDF content is calculated. The `extractions` database table is queried to check if this `file_hash` already exists.
    -   **If YES**: The existing `extraction_id` is returned immediately. The pipeline stops.
    -   **If NO**: The pipeline continues.
3.  **OCR Processing**: The raw PDF bytes are converted to plain text using `pytesseract` and the `pdf2image` library. This happens in `main.py`.
4.  **Initial NER Extraction**: The raw text is processed by a `spaCy` model (`fr_core_news_lg`) to perform Named Entity Recognition (NER). Basic contact info (emails, phones) is extracted using regex. This provides a baseline `initial_extraction` JSON object.
5.  **LLM Refinement**:
    -   **Module**: `llm_refiner.py`
    -   **Function**: `refine_extraction_with_llm()`
    -   **Input**: `raw_text` (string) and `initial_extraction` (dict).
    -   **Process**: The raw text and initial JSON are formatted into a prompt. This prompt is sent to a Hugging Face Inference API endpoint.
    -   **Current Model**: `facebook/bart-large-cnn` (a summarization model used as a stable placeholder).
    -   **Output**: A tuple `(bool, dict)` indicating success and the refined JSON data.
6.  **Data Persistence**:
    -   The original PDF is uploaded to a Supabase Storage bucket (`cvs`).
    -   A new record is inserted into the `extractions` table in the Supabase database. This record contains the `file_hash`, storage path, and the final refined JSON data.
7.  **HTTP Response**: The `extraction_id` of the newly created record is returned to the user.

## 3. Key Modules & Components

### `main.py`
- **Responsibility**: The main FastAPI application entrypoint. Handles HTTP requests, orchestrates the entire processing pipeline, and interacts with the database.
- **Key Endpoints**:
    - `/upload`: The primary endpoint that triggers the CV processing pipeline.
    - `/anonymize/{extraction_id}`: Fetches processed data, generates an anonymized `.docx` file, and returns a download link.
    - `/status`: A health-check endpoint.
- **Dependencies**: `fastapi`, `uvicorn`, `pytesseract`, `spacy`, `supabase-py`, `python-docx`.

### `llm_refiner.py`
- **Responsibility**: Handles all interaction with the OpenAI API for data refinement.
- **Key Function**: `refine_extraction_with_llm(raw_text, initial_extraction)`
- **Data Structures**:
    - **Input**: A raw text string and a dictionary (`initial_extraction`) containing entities found by `spaCy`.
    - **Output**: Returns a tuple `(success: bool, result: dict)`. If `success` is `False`, the dictionary contains error details. If `True`, it contains the refined data.
- **Models**:
    - **Current**: `gpt-4o`
- **Prompting Strategy**: A detailed system prompt instructs the model to not only extract data but also to actively clean and refine it. This includes correcting OCR errors, removing artifacts, and reformulating text for clarity. The model is constrained to output a valid JSON object using the `json_object` response format.

### `logger_config.py`
- **Responsibility**: Configures the application-wide logger.
- **Functionality**: Sets up a `StreamHandler` to print formatted logs to the console. The log level is determined by the `DEBUG` environment variable (`DEBUG=True` sets level to `DEBUG`, otherwise `INFO`). This module is imported once at the top of `main.py` to apply the configuration.

### `monitor.py`
- **Responsibility**: A standalone CLI tool for real-time monitoring of the API's health.
- **Functionality**: When executed (`python monitor.py`), this script periodically polls the `/status` endpoint of the running FastAPI application. It uses the `rich` library to display the fetched CPU, memory, and disk usage in a live-updating terminal dashboard.
- **Dependencies**: `rich`, `httpx`.

### `migrations/`
- **Responsibility**: Contains raw SQL files for setting up and evolving the database schema.
- **Usage**: These are intended to be applied manually or via a migration tool to the Supabase PostgreSQL database.
- **Key Table**: `public.extractions`
    - `id`: Primary key.
    - `created_at`: Timestamp.
    - `filename`: Original name of the uploaded file.
    - `storage_path`: Path to the file in Supabase Storage.
    - `data`: A `jsonb` column containing the final, refined extraction data.
    - `file_hash`: A `VARCHAR(64)` with a `UNIQUE` constraint, used for deduplication.

## 4. Environment Variables (`.env`)

The application is configured via a `.env` file in the root directory.

- `SUPABASE_URL`: The URL of your Supabase project.
- `SUPABASE_ANON_KEY`: The public "anon" key for your Supabase project.
- `OPENAI_API_KEY`: Your API key from OpenAI, used for the GPT-4o refinement process.
- `DEBUG`: Set to `"True"` to enable debug-level logging and more verbose error responses.

## 5. Template Context

The `template_generator.py` module prepares a context dictionary that is passed to the `cv_template.docx` for rendering. Here are the available variables:

- `initials` (str): The initials of the person's name.
- `title` (str): The person's title (e.g., "Software Engineer").
- `experience_years` (int): The total years of experience, calculated from the `period` of each experience.
- `current_company` (str): The company of the most recent experience.
- `experiences` (list of dicts): A list of work experiences. Each dictionary has the following keys:
    - `title` (str)
    - `company` (str)
    - `period` (str)
    - `description` (str)
    - `technologies` (list of str)
- `certifications` (list of dicts): A list of certifications. Each dictionary has:
    - `title` (str)
    - `year` (str)
    - `institution` (str)
- `skills` (dict): A dictionary where keys are skill categories (e.g., "frontend", "backend") and values are lists of skill names.
- `languages` (list of dicts): A list of languages. Each dictionary has:
    - `name` (str)
    - `level` (str)

## 6. Template Debugging

When creating or modifying the `.docx` template (`templates/cv_template.docx`), it's possible to introduce Jinja2 syntax errors.

- **Trigger**: A `jinja2.exceptions.TemplateSyntaxError` will be raised during a call to the `/anonymize/{id}` endpoint.
- **Debugging Feature**: If the application is running with `DEBUG=True` in the environment, the `template_generator.py` module will catch this specific error.
- **Action**: It will save the raw, pre-rendered XML of the document body to a file named `templates/debug_template.xml`.
- **How to Use**: Open `debug_template.xml` in a text editor. The content is the raw `document.xml` from the `.docx` file. You can search this file for the malformed Jinja2 tags (e.g., `{{ an_incorrect_variable }}`) to find the exact location of the error, which is often difficult to do by looking at the `.docx` file directly.
