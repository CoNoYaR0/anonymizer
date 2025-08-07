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
