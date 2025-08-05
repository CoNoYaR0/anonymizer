# Agent Instructions for `cv-anonymizer-backend`

This document provides a technical overview of the project, intended for an AI software engineer (like Jules). Its purpose is to outline the architecture, data flow, and key components to facilitate efficient task completion.

## 1. Core Objective

The project provides two main pieces of functionality:
1.  A REST API to extract structured data from PDF CVs and populate a pre-defined `.docx` template.
2.  An advanced, standalone tool to convert any user-supplied `.docx` CV into a high-quality, reusable Jinja2 template.

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
This is the core advanced feature. It uses a 3-stage, LLM-driven process to convert a `.docx` CV into a reusable Jinja2 template, ensuring high quality and correctness.

-   **Endpoint**: `POST /convert-to-template`
-   **Input**: A single `.docx` file.
-   **Output**: A ready-to-use `.docx` Jinja2 template file, or a JSON error object if validation fails.

#### The 3-Stage Pipeline:

1.  **Stage 1: LLM Data Extraction (`docx_to_template_converter.py`)**
    -   The text content of the uploaded `.docx` is extracted.
    -   This text is sent to an LLM (GPT-4o) with a prompt instructing it to act as an expert data extractor and return a clean, structured JSON object of the CV's contents (experiences, skills, education, etc.). This is a much more reliable task for the LLM than generating code directly.

2.  **Stage 2: Programmatic Template Generation (`docx_to_template_converter.py`)**
    -   This stage takes the original `.docx` file and the structured data from Stage 1.
    -   A Python function (`_build_replacement_map`) programmatically generates the precise Jinja2 template code, including loops and filters. This ensures the generated Jinja2 syntax is always perfect.
    -   A robust, paragraph-aware replacement engine (`_replace_text_block`) then finds and replaces the original text blocks in the document with the machine-generated Jinja2 code.

3.  **Stage 3: LLM QA Review (`template_qa.py`)**
    -   The newly generated template from Stage 2 is passed to a second, specialized LLM call for final validation.
    -   This QA LLM checks for correctness against a strict set of rules.
    -   **Decision:** If the template is valid, it's sent to the user. If not, a `400 Bad Request` is returned, including the list of issues identified by the QA LLM for full transparency.

## 3. Key Modules & Components

### `main.py`
- **Responsibility**: The main FastAPI application entrypoint. Handles HTTP requests and orchestrates the pipelines.
- **Key Endpoints**:
    - `/upload`, `/anonymize/{extraction_id}`: For the PDF anonymization workflow.
    - `/convert-to-template`, `/converter`: For the DOCX to Template conversion workflow.

### `docx_to_template_converter.py`
- **Responsibility**: Implements Stage 1 (Analysis) and Stage 2 (Generation) of the DOCX to Template pipeline.
- **Key Functions**:
    - `_get_structured_data_from_llm`: Extracts structured data from the CV text.
    - `_build_replacement_map`: Programmatically generates the Jinja2 code and replacement map.
    - `_replace_text_block`: The robust engine for replacing multi-paragraph blocks in the document.

### `template_qa.py`
- **Responsibility**: Implements Stage 3 (QA Review) of the DOCX to Template pipeline.
- **Key Function**: `validate_template_with_llm(docx_stream)`

### `llm_refiner.py`
- **Responsibility**: Handles the LLM call for the simpler PDF-to-JSON workflow.

### `tests/`
- **Responsibility**: Contains the test suite for the application.
- **Key File**: `tests/test_converter.py`
- **Mocking**: The tests for the template converter use `monkeypatch` to mock the LLM calls in Stage 1 and Stage 3, ensuring tests are fast, deterministic, and do not require API keys.

## 4. Environment Variables (`.env`)

- `OPENAI_API_KEY`: Required for both the PDF anonymization and the DOCX template conversion workflows.
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`: Required for the PDF anonymization workflow.
- `DEBUG`: Set to `"True"` to enable detailed debug logging.
