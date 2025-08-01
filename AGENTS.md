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
- **Responsibility**: Handles all interaction with the external Large Language Model (LLM) via the Hugging Face Inference API.
- **Key Function**: `refine_extraction_with_llm(raw_text, initial_extraction)`
- **Data Structures**:
    - **Input**: A raw text string and a dictionary (`initial_extraction`) containing entities found by `spaCy`.
    - **Output**: Returns a tuple `(success: bool, result: dict)`. If `success` is `False`, the dictionary contains error details. If `True`, it contains the refined data.
- **Models**:
    - **Default (Testing)**: `facebook/bart-large-cnn`
    - **Target (Production)**: GPT-4o (to be implemented later).

### `logger_config.py`
- **Responsibility**: Configures the application-wide logger.
- **Functionality**: Sets up a `StreamHandler` to print formatted logs to the console. The log level is determined by the `DEBUG` environment variable (`DEBUG=True` sets level to `DEBUG`, otherwise `INFO`). This module is imported once at the top of `main.py` to apply the configuration.

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
- `HUGGINGFACE_API_KEY`: Your API token for authenticating with the Hugging Face Inference API.
- `DEBUG`: Set to `"True"` to enable debug-level logging and more verbose error responses.
