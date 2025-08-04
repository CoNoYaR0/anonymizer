# Agent Instructions for `cv-anonymizer-backend`

This document provides a technical overview of the project, intended for an AI software engineer (like Jules). Its purpose is to outline the architecture, data flow, and key components to facilitate efficient task completion.

## 1. Core Objective

The primary goal of this project is to create a FastAPI backend that accepts a CV (PDF), processes it through a multi-stage pipeline, and returns a link to an anonymized `.docx` version of the CV.

## 2. System Architecture & Data Flow

The application has two primary workflows.

### Workflow 1: PDF Anonymization (`/upload` & `/anonymize`)
This flow is designed to extract structured data from a PDF CV and use it to populate a fixed template.
1.  **HTTP Request (`/upload`)**: Receives a PDF file.
2.  **Deduplication & OCR**: Converts the PDF to raw text.
3.  **LLM Refinement (`llm_refiner.py`)**: Uses GPT-4o to extract structured `JSON` data from the raw text.
4.  **Data Persistence**: Saves the extracted JSON to the database, returning an `extraction_id`.
5.  **Anonymization (`/anonymize/{id}`)**: The user calls this endpoint with the ID. The system uses `template_generator.py` to inject the stored JSON into a predefined `.docx` template (`templates/cv_template.docx`) and returns a download link.

### Workflow 2: DOCX to Template Conversion (`/convert-to-template`)
This is a more advanced, self-contained pipeline designed to convert any given `.docx` CV into a reusable Jinja2 template. It follows a 3-stage, LLM-driven process to ensure quality and correctness.

-   **Endpoint**: `POST /convert-to-template`
-   **Input**: A single `.docx` file.
-   **Output**: A ready-to-use `.docx` Jinja2 template file, or a JSON error object if validation fails.

#### The 3-Stage Pipeline:

1.  **Stage 1: LLM Semantic Analysis (`docx_to_template_converter.py`)**
    -   The text content of the uploaded `.docx` is extracted.
    -   This text is sent to an LLM (GPT-4o) with a detailed system prompt.
    -   The prompt instructs the LLM to act as an expert template engineer, identifying all dynamic content (names, experiences, skills, etc.) and defining how it should be templated.
    -   The LLM returns a structured JSON "semantic map" containing two types of instructions:
        -   `simple_replacements`: For basic text-to-placeholder swaps (e.g., `"John Doe"` -> `"{{ name }}"`).
        -   `block_replacements`: For complex, multi-paragraph sections, where the LLM provides the full Jinja2 loop code (e.g., `{% for job in experiences %}{{ job.title }}{% endfor %}`).

2.  **Stage 2: Template Generation (`docx_to_template_converter.py`)**
    -   This stage takes the original `.docx` file and the semantic map from Stage 1.
    -   It uses a robust, paragraph-aware replacement engine to apply the instructions from the map.
    -   It iterates through all paragraphs (including those in tables) to perform both simple and block-level replacements.
    -   The output is a new in-memory `.docx` file containing the Jinja2 template code.

3.  **Stage 3: LLM QA Review (`template_qa.py`)**
    -   The newly generated template from Stage 2 is passed to a second, specialized LLM call for validation.
    -   This QA LLM is given a strict set of rules (correct Jinja2 syntax, placeholder naming conventions, no unclosed loops, etc.).
    -   It returns a JSON object indicating if the template is `is_valid` and a list of `issues` if any are found.
    -   **Decision:** If the template is valid, it's sent to the user. If not, the pipeline stops, and a `400 Bad Request` is returned to the user, including the list of issues identified by the QA LLM for full transparency.

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

---

### `docx_to_template_converter.py`
- **Responsibility**: Implements Stage 1 (Analysis) and Stage 2 (Generation) of the DOCX to Template pipeline.
- **Key Function**: `convert_docx_to_template(docx_stream, ...)`
- **Key Algorithm (`_replace_text_block`)**: Contains the robust logic for finding and replacing multi-paragraph blocks of text, searching within the main body and all table cells.

### `template_qa.py`
- **Responsibility**: Implements Stage 3 (QA Review) of the DOCX to Template pipeline.
- **Key Function**: `validate_template_with_llm(docx_stream)`
- **Functionality**: Extracts text from the generated template and uses a specialized LLM prompt to check for Jinja2 syntax errors and adherence to the project's specific templating conventions.

### `tests/`
- **Responsibility**: Contains the test suite for the application.
- **Key File**: `tests/test_converter.py`
- **Functionality**: Uses `pytest` and FastAPI's `TestClient` to perform integration testing.
- **Mocking**: The tests for the template converter use `monkeypatch` to mock the LLM calls in Stage 1 and Stage 3, ensuring tests are fast, deterministic, and do not require API keys.

---
*In `main.py`, the following endpoints are relevant to the converter workflow:*

- `/converter`: A `GET` endpoint that serves the `templates/converter.html` page.
- `/convert-to-template`: A `POST` endpoint that orchestrates the full 3-stage pipeline for converting a `.docx` file into a Jinja2 template.
