### Jules's Workstation
*   **STATUS:** Active
*   **NEXT TASK:** Implement the real CV content extraction logic in `src/content_extractor.py`. This involves using OCR for PDFs/images and `python-docx` for DOCX files, then sending the extracted text to the OpenAI API to get structured JSON data.

---
# Developer Log: CV Anonymizer Backend

This document tracks the development progress, decisions made, and future roadmap for the CV Anonymizer backend project.

## Project Overview

The goal of this project is to create a backend service that can take a CV in PDF format, extract its content, identify and anonymize personal information, and generate a new, anonymized document. A key feature is a standalone tool to convert any `.docx` CV into a high-quality, reusable Jinja2 template.

## Development History & Key Decisions

### Initial PDF Anonymization Pipeline
*   **Objective:** Build the core functionality for OCR, entity extraction, and document anonymization from PDF files.
*   **Implementation:** A multi-step process was created involving `pytesseract` for OCR, `llm_refiner.py` to extract structured JSON using GPT-4o, and `template_generator.py` to inject this JSON into a fixed `.docx` template. This workflow is handled by the `/upload` and `/anonymize` endpoints.

### Feature: DOCX to Jinja2 Template Converter
*   **Objective:** Fulfill the user request to build a standalone tool for converting completed `.docx` CVs into `docxtpl`-compatible Jinja2 templates.
*   **Initial Approach & Challenges:** The first implementation attempted to use a single LLM call to both identify dynamic content and generate Jinja2 code. This proved to be unreliable, as the LLM would often produce syntactically incorrect Jinja2 (e.g., missing `{% endfor %}` tags). The text replacement logic was also too brittle and failed to find text blocks within the document's complex structure (including tables).

*   **Final Architecture (Multi-Stage LLM Pipeline):** To solve these issues and ensure a deterministic, high-quality output, the feature was completely re-architected into a 3-stage pipeline:
    1.  **Stage 1 (LLM Data Extraction):** The system first uses an LLM call with one simple, reliable task: extract the content of the CV into a clean, structured JSON object.
    2.  **Stage 2 (Programmatic Template Generation):** A new Python function (`_build_replacement_map`) takes the structured data from Stage 1 and programmatically generates the replacement map. The Python code, not the LLM, is responsible for writing the Jinja2 code, including loops and filters. This guarantees syntactically perfect template code every time. A robust, paragraph-aware replacement engine (`_replace_text_block`) was also developed to correctly apply these changes to the `.docx` file, even for complex, multi-paragraph blocks inside tables.
    3.  **Stage 3 (LLM QA Review):** A new `template_qa.py` module acts as a final safety net. It uses a second, specialized LLM call to validate the final generated template against a strict set of rules. This ensures that the final output is always correct and ready to use.

*   **Frontend Enhancements:** The frontend was updated with functional JavaScript for drag-and-drop and to gracefully handle and display detailed error messages from the backend (e.g., from a failed QA review or a corrupted file).

*   **Testing:** A `pytest` suite was created from scratch. The final version uses `monkeypatch` to mock all external LLM calls, allowing for fast, deterministic, and cost-effective testing of the entire pipeline.

*   **Git Hygiene:** Resolved a merge conflict caused by a cached `__pycache__` file and updated `.gitignore` to prevent future issues.

### Phase 3: Architectural Migration to "PDF/HTML-First"
*   **Date:** 2025-08-05
*   **Objective:** To address the fundamental fragility and high cost of the `.docx`-based templating engine, a strategic decision was made to migrate to a more robust, web-native architecture.
*   **New Architecture:**
    *   **Workflow 1 (Template Creation):** A user's styled PDF will be converted by a vision-capable LLM into high-fidelity HTML/CSS, which will then be turned into a reusable Jinja2 template.
    *   **Workflow 2 (CV Anonymization):** New CVs will be processed to extract a canonical JSON object, which will then be rendered into the user's HTML template and delivered as a clean PDF or HTML string.
*   **Reasoning:** This approach eliminates the error-prone `.docx` format from the output pipeline, gives us full programmatic control over templating, reduces LLM costs by removing the complex QA/refinement loop, and produces a more professional and reliable end product. This marks the final and most robust iteration of the system.
*   **Post-Migration Fixes:** Corrected the package name for `mammoth` in `requirements.txt`. Fixed a critical bug in the PDF-to-HTML conversion logic where raw PDF data was being sent to the vision model instead of images. Corrected the FastAPI response type for streaming HTML content.
*   **Final Implementation:** Completed the implementation of both the "Template Creation" and "CV Anonymization" workflows. The system is now fully functional on the new architecture. Project Complete.
*   **Templating Engine Pivot (Liquid):** On direct feedback, the decision was made to switch the templating engine from Jinja2 to Liquid to better align with broader industry standards (e.g., Shopify, Jekyll). The `template_builder.py` module was refactored to support this change. The system now uses the `liquidpy` library for parsing and validation. Crucially, the `LLM + QA + retry` loop was re-implemented for Liquid, ensuring that any syntax errors generated by the LLM are automatically caught and corrected before a template is finalized. The LLM prompts for both HTML generation and Liquid templating were also refined for higher fidelity and accuracy.

### Phase 4: Final Architecture - The "Convertio-First" Model
*   **Date:** 2025-08-05
*   **Objective:** To achieve 100% deterministic and visually perfect template creation, the project underwent a final architectural pivot, replacing the LLM-based visual conversion with a dedicated, professional API.
*   **New Architecture (Template Creation):**
    1.  The user now uploads a styled `.docx` file.
    2.  The backend calls the **Convertio API** to perform a high-fidelity conversion to a styled HTML file.
    3.  This perfect HTML is then processed by an LLM for the sole purpose of injecting Liquid placeholders.
*   **Reasoning:** This is the most robust and reliable architecture. It completely removes the risk of layout "hallucinations" from vision models and guarantees that the template's look and feel are a perfect match for the user's original document.
*   **Implementation & Cleanup:**
    -   `template_builder.py` was completely refactored to integrate with the Convertio API.
    -   The API endpoint in `main.py` was updated to `/templates/create-from-docx`.
    -   All legacy code and modules related to the old `.docx-to-jinja` and `pdf-to-html` workflows were identified and deleted.
    -   The test suite was refactored to mock the new Convertio API calls.
    -   The entire codebase was cleaned and finalized, marking the completion of the project's development.

---
## Phase 5: Project Reconstruction by Jules
*   **Date:** 2025-08-07
*   **Objective:** Complete rebuild of the entire codebase from scratch based on canonical reference files to establish a clean, maintainable, and robust foundation for future development.
*   **Action: "Clean Slate" Codebase Reconstruction**
    *   **Task:** Rebuild the full codebase from scratch based on the canonical reference files (`AGENTS.md`, `DEVLOG.md`, `HOW_TO_USE.md`, `README.md`).
    *   **Implementation:**
        *   Generated a complete project skeleton following the "Convertio-First" architecture.
        *   Created all core modules (`main.py`, `database.py`, `template_builder.py`, `content_extractor.py`, `renderer.py`) with placeholder logic and `TODO` comments.
        *   Established the database schema and a new migration script (`apply_migrations.py`).
        *   Set up project configuration files (`requirements.txt`, `.gitignore`, `.env.example`).
*   **Status:** The new project skeleton is complete and submitted. It is now ready for the implementation of the core application logic within the placeholder functions.
*   **Action: Supabase Integration for Production Readiness**
    *   **Date:** 2025-08-07
    *   **Task:** Integrate the application with a Supabase backend for database and file storage, moving it from a skeleton to a production-ready foundation.
    *   **Implementation:**
        *   Refactored the database connection logic (`database.py`, `apply_migrations.py`) to dynamically construct the connection string from Supabase-specific environment variables.
        *   Added a new `storage.py` module to handle all file operations (upload, download) with Supabase Storage.
        *   Updated `main.py` to replace all temporary local file handling with robust calls to the new storage module, making the application stateless.
        *   Updated `requirements.txt` and `.env.example` to include the `supabase-py` library and new environment variables.
*   **Status:** The application is now fully integrated with Supabase.
*   **Action: Bug Fix - Database Connection**
    *   **Date:** 2025-08-07
    *   **Issue:** The application was failing to connect to the Supabase database due to an IPv6 resolution issue with the default database host.
    *   **Fix:**
        *   Modified the database connection logic in `src/database.py` to use the IPv4-compatible **session pooler** host provided by Supabase.
        *   Added a `DB_HOST` environment variable to make this configurable.
        *   Updated `HOW_TO_USE.md` to reflect this new requirement.
*   **Status:** The database connection is now stable and uses the recommended Supabase pooler.
*   **Action: Correction - Improved Connection Instructions**
    *   **Date:** 2025-08-07
    *   **Issue:** The previous fix for the database connection was correct in its approach (using the pooler) but poor in its implementation. The `.env.example` and `HOW_TO_USE.md` files contained a placeholder (`aws-0-your-region...`) that caused confusion and errors. This was a result of insufficient research on my part.
    *   **Fix:**
        *   Updated `.env.example` and `HOW_TO_USE.md` with explicit, unambiguous instructions for the user to find and copy their unique database pooler host from their Supabase project dashboard.
        *   This ensures the user provides the correct, project-specific host, eliminating the "could not translate host name" error.
*   **Status:** The documentation is now clear and correct, preventing user error during setup.
*   **Action: Bug Fix - Database Authentication**
    *   **Date:** 2025-08-07
    *   **Issue:** After fixing the host, a new error `FATAL: Tenant or user not found` appeared.
    *   **Fix:** The connection pooler requires the username to be in the format `postgres.<project_ref>`. The code was hardcoding the user as `postgres`. I updated `src/database.py` to dynamically construct the correct username using the project reference ID from the `SUPABASE_URL`.
*   **Status:** The database connection is now fully functional.
*   **Action: Implemented Caching Logic**
    *   **Date:** 2025-08-07
    *   **Task:** Replace the placeholder `TODO`s in `src/database.py` with functional database logic.
    *   **Implementation:**
        *   Implemented the `get_cached_html` function to perform a `SELECT` query on the `html_cache` table.
        *   Implemented the `cache_html` function to perform an `INSERT ... ON CONFLICT DO UPDATE` (upsert) operation, making the caching robust against duplicate file submissions.
*   **Status:** The database caching layer is now fully implemented and operational.
*   **Action: Implemented Supabase Storage Logic**
    *   **Date:** 2025-08-07
    *   **Task:** Replace the placeholder `TODO`s in `src/storage.py` with functional Supabase Storage logic.
    *   **Implementation:**
        *   Implemented the `upload_file_to_storage` function to upload files to a specified bucket and return a public URL.
        *   Implemented the `download_file_from_storage` function to retrieve file content from a bucket.
        *   Handled a limitation in the `supabase-py` library by temporarily saving file bytes to disk before uploading.
*   **Status:** The file storage layer is now fully implemented and operational.
*   **Action: Implemented Convertio API Integration**
    *   **Date:** 2025-08-07
    *   **Task:** Replace the placeholder `TODO` in `template_builder._convert_docx_to_html` with a functional implementation.
    *   **Implementation:**
        *   Implemented the full, multi-step Convertio API workflow: start conversion, upload file, poll for status, and download the resulting HTML.
        *   The function now takes file bytes as input and handles the temporary file creation required for the API call.
*   **Status:** The DOCX-to-HTML conversion pipeline is now fully functional.
*   **Action: Architectural Pivot - Manual Validation Workflow**
    *   **Date:** 2025-08-07
    *   **Reasoning (based on user feedback):** The fully automated workflow is efficient but lacks flexibility for the iterative development of the AI injection step. A manual validation loop is necessary to refine AI prompts and ensure template quality without losing the original, clean HTML conversion.
    *   **Implementation:**
        *   Refactored the template creation process into a three-step workflow with dedicated API endpoints:
            1.  `POST /templates/create-from-docx`: Converts DOCX to raw HTML and stores it.
            2.  `POST /templates/inject`: Runs the AI injection on the stored HTML and returns it for review without saving.
            3.  `POST /templates/validate-and-save`: Allows the user to save the validated/corrected Liquid template, overwriting the raw HTML and finalizing the template.
        *   Updated `template_builder.py` to separate the conversion and injection logic to support this new workflow.
*   **Status:** The application now supports a robust, flexible, and developer-friendly workflow for creating and validating templates.
*   **Action: Bug Fix - Convertio API Integration**
    *   **Date:** 2025-08-07
    *   **Issue:** The Convertio API was returning a `KeyError: 'upload_url'` because the two-step upload process was not supported as expected. The API was not returning an `upload_url`.
    *   **Fix:**
        *   Refactored the `convert_docx_to_html_and_cache` function to use the `base64` input method.
        *   The file content is now encoded in Base64 and sent in a single, atomic request to the Convertio API, which is more robust and resolves the error.
*   **Status:** The Convertio API integration is now correct and functional.
*   **Action: Implemented AI Placeholder Injection**
    *   **Date:** 2025-08-07
    *   **Task:** Replace the placeholder `TODO` in `template_builder.inject_liquid_placeholders` with a functional implementation.
    *   **Implementation:**
        *   The function now uses `BeautifulSoup` to parse the HTML and extract all relevant text nodes.
        *   It constructs a detailed prompt for the OpenAI GPT-4o model, asking it to act as a templating expert and return a JSON map of original text to Liquid placeholders.
        *   It calls the OpenAI API and specifies a JSON response format.
        *   After receiving the map, it uses `BeautifulSoup` again to safely find and replace the text nodes with their corresponding Liquid placeholders, preserving the HTML structure.
*   **Status:** The core AI feature of the template creation workflow is now fully implemented.
*   **Action: Improved Scalability of AI Injection**
    *   **Date:** 2025-08-07
    *   **Issue:** The OpenAI API call was failing with a `rate_limit_exceeded` error for large documents, as the entire text content was being sent in a single request.
    *   **Fix:**
        *   Implemented a chunking mechanism in the `inject_liquid_placeholders` function.
        *   The extracted text is now split into smaller chunks, and each chunk is sent to the OpenAI API in a separate request.
        *   The resulting JSON maps are then merged before the final replacement step.
*   **Status:** The AI injection process is now robust and can handle large documents without hitting API token limits.
*   **Action: Bug Fix - AI Injection Rate Limiting**
    *   **Date:** 2025-08-07
    *   **Issue:** The chunking logic solved the request size limit, but triggered a new `rate_limit_exceeded` error due to too many requests per minute (TPM).
    *   **Fix:** Added a 2-second delay (`time.sleep(2)`) between each chunked API call to OpenAI.
*   **Status:** The AI injection process now respects the API's rate limits and can process large documents successfully.
*   **Action: Architectural Refactor - Token-Efficient AI Injection**
    *   **Date:** 2025-08-07
    *   **Issue:** The previous text-chunking method for AI injection was still inefficient and prone to rate-limiting issues.
    *   **Fix (Hybrid ID-based Approach):**
        *   Refactored the `inject_liquid_placeholders` function to use a more sophisticated, token-efficient method.
        *   The process now assigns a unique `data-liquid-id` to each text-containing element in the HTML.
        *   It sends a lightweight JSON object mapping these IDs to their text content to the AI, instead of the full raw text.
        *   The AI returns a map of IDs to Liquid variables, which are then precisely injected back into the elements by finding their unique IDs.
*   **Status:** The AI injection process is now highly efficient, robust, and permanently solves the token/rate-limiting problems while guaranteeing HTML structural integrity.
*   **Action: Refactor - Simplified DB Connection Logic**
    *   **Date:** 2025-08-07
    *   **Issue:** The previous fix for the database authentication was overly complex. It parsed the `SUPABASE_URL` to build the username dynamically, when a simpler solution was available.
    *   **Fix (based on user feedback):**
        *   Refactored `src/database.py` to use a direct `DB_USER` environment variable instead of parsing the URL. This is a much cleaner and more explicit solution.
        *   Updated `.env.example` and `HOW_TO_USE.md` to reflect this simpler setup, instructing the user to copy the `DB_USER` directly from their Supabase dashboard.
*   **Status:** The database connection logic is now both correct and simple, following best practices.

### Phase 6: Collaborative Debugging & Final Solution
*   **Date:** 2025-08-09
*   **Objective:** To debug and resolve a series of complex, interacting issues with the AI-powered template generation, ultimately arriving at a robust, deterministic, and high-quality solution through a collaborative process.
*   **Action: Debugging OpenAI Authentication**
    *   **Issue:** The application was failing with a `401 Unauthorized` error from the OpenAI API.
    *   **Investigation:**
        *   Initial hypothesis was an incorrect API key in the `.env` file.
        *   User confirmed the key was correct via a `curl` test, deepening the mystery.
        *   A `grep` command revealed the incorrect key was still present in the `.env` file.
        *   **Final Discovery (by user):** The `.env` file was set to "read-only", preventing any changes from being saved. This was the root cause of the authentication issue.
*   **Action: Collaborative Refinement of AI Templating**
    *   **Initial State:** The base AI logic worked for most of the document but failed on specific, complex lines (e.g., header, skills, technologies).
    *   **Attempt 1 (AI Logic - Failure):** An attempt to fix the remaining issues by allowing multiple classifications per text node in `ai_logic.py` caused a major regression, as it confused the AI. This change was reverted.
    *   **Attempt 2 (AI Logic - Randomness):** After reverting, it was discovered through user observation that the AI's output was non-deterministic (random), producing different results on each run.
    *   **Attempt 3 (AI Logic - Model Incompatibility):** The standard fix for randomness (`temperature=0`) was applied. This revealed a fatal flaw in the environment: the specified `gpt-5` model did not support this parameter.
    *   **Attempt 4 (AI Logic - Model Swap):** On the user's suggestion, the model was switched to `gpt-4o`. This fixed the randomness, but the prompt, which was tuned for `gpt-5`, produced very poor quality results with the new model.
*   **Action: Final Architecture - Context-Aware Pre-processing**
    *   **Reasoning (based on collaborative brainstorming):** After exhausting all simple AI logic fixes, we concluded that the root problem was asking the AI to parse overly complex text. The definitive solution was to pre-process the HTML programmatically to simplify the AI's task.
    *   **Implementation:**
        *   A new `_contextual_preprocess_and_get_map` function was implemented in `template_builder.py`.
        *   This function intelligently determines the document "section" for each piece of text (header, skills, etc.).
        *   It also programmatically splits complex "Label: Value" lines into separate, simple nodes.
        *   The prompt in `ai_logic.py` was upgraded to use this new contextual information, making the AI's job easier and its results more accurate.
        *   A final bug (`NameError: 're' not defined`) was caught and fixed by adding the required import.
*   **Status:** The template generation workflow is now stable, deterministic, and produces high-quality results. The collaborative debugging process has resulted in a significantly more robust and intelligent architecture.
