# Developer Log: CV Anonymizer Backend

This document tracks the development progress, decisions made, and future roadmap for the CV Anonymizer backend project.

## Project Overview

The goal of this project is to create a backend service that can take a CV in PDF format, extract its content, identify and anonymize personal information, and generate a new, anonymized document.

## Development History & Key Decisions

### Initial Implementation (Phases 1 & 2)

*   **Objective:** Build the core functionality for OCR, entity extraction, and document anonymization.
*   **Initial Approach (Blocked):** The first attempt was to use `Tesseract` and `Poppler` for OCR, as specified in the project's `README.md`. This was blocked in the initial cloud environment due to a lack of system permissions to install these packages.
*   **Pivot 1: `easyocr`:** To overcome the dependency issue, we pivoted to `easyocr`, a pure-Python library.
    *   **Challenge:** While this allowed the application to run, local testing revealed two major problems:
        1.  **Memory Usage:** The `easyocr` and `spaCy` models were too memory-intensive for Render's free tier, causing `Out of Memory` errors.
        2.  **Poor Quality:** The OCR quality on the sample CV was very low, leading to garbled text and inaccurate entity extraction.
*   **Pivot 2 (Current Approach): `pytesseract` for Local Development:** Based on the poor quality of `easyocr`, the decision was made to prioritize accuracy. We switched back to a more robust OCR engine, `pytesseract`. To avoid the initial deployment blockers, the development focus was shifted to a local-first approach, where the necessary system dependencies (`Tesseract` and `Poppler`) can be installed freely.
*   **Model Upgrade:** For local development, we upgraded the spaCy model to `fr_core_news_lg` (the large model) to ensure the highest possible accuracy for Named Entity Recognition.

### Feature Additions

*   **Database Schema:** Created a comprehensive set of SQL migration files to define the database structure for Supabase (PostgreSQL). This includes tables for candidates, experiences, skills, etc., with appropriate indexing.
*   **Monitoring & Usability:**
    *   Added a `/status` endpoint using `psutil` to provide real-time monitoring of the server's CPU, RAM, and disk usage.
    *   Ensured the auto-generated FastAPI documentation (Swagger UI at `/docs` and ReDoc at `/redoc`) is accessible and documented in the `HOW_TO_USE.md`.

## Current Project Status

As of now, we have successfully completed the core backend functionality as outlined in **Phase 1** and **Phase 2** of the `README.md`. The application is in a state where it can be run and tested effectively in a local environment.

### Completed:

*   ✅ **Phase 1: MVP Technique** - OCR and NER pipeline is in place.
*   ✅ **Phase 2: Anonymisation et génération document** - Anonymization logic and `.docx` generation are functional.
*   ✅ **Database Schema:** SQL migrations are ready for database initialization.
*   **API Monitoring:** A `/status` endpoint provides resource metrics for the application process.
*   **Live CLI Dashboard:** Added a standalone `monitor.py` script that uses the `rich` library to provide a live-updating terminal dashboard for the `/status` endpoint.
*   **API Documentation:** Interactive documentation is automatically available via Swagger UI (`/docs`).
*   **API Workflow Refactor:** The anonymization process was refactored into a cleaner, two-step, ID-based workflow (`/upload` followed by `/anonymize/{id}`).

### To Be Done (Next Steps):

*   ➡️ **Phase 3: Frontend avancé et gestion utilisateur**
    *   This is the next major part of the project. It involves creating a separate frontend application (e.g., using React) that will consume this backend API.
*   ➡️ **Phase 4: Intégration d’un LLM open-source**
    *   **Initial Plan:** Use an LLM to parse the raw OCR text directly.
    *   **Revised Plan (Hybrid Approach):** A more sophisticated and efficient approach was adopted. We will use `spaCy` for a fast "first pass" extraction of simple entities. Then, we will feed both the raw text and this initial JSON to an LLM (e.g., Mistral on Hugging Face). The LLM's task will be to refine and complete this JSON, correcting OCR errors and extracting more complex, contextual information like job experiences and skills. This method is more token-efficient and provides more reliable, structured output.
### LLM Selection & Deduplication (Post-Phase 2)

*   **Objective:** Stabilize the LLM refinement process and improve storage efficiency.
*   **Challenge (LLM Unavailability):** After implementing the initial LLM refinement logic, extensive testing revealed that the chosen `mistralai` models, and even alternatives like `google/flan-t5-large`, were consistently returning `404 Not Found` errors from the Hugging Face free Inference API. This suggests a potential change in availability for these high-demand models on the free tier.
*   **Pivot 3 (Stable Fallback Model):** After testing over 70 candidate models, `facebook/bart-large-cnn` was identified as the most reliable model that consistently returned a `200 OK` status. While it is a summarization model, the prompt has been adapted to leverage it for an extraction-like task.
    *   **Decision:** `facebook/bart-large-cnn` will be used as the default model for the current development and testing phase to ensure the pipeline is functional end-to-end.
    *   **Future Goal:** The target for the production environment remains a more powerful, instruction-tuned model, likely via a paid service (e.g., GPT-4o or a Hugging Face Pro endpoint).
*   **Feature (Deduplication):** Implemented a file deduplication system. Before processing, the SHA256 hash of an uploaded PDF is calculated and checked against the database. If the hash exists, the existing `extraction_id` is returned, preventing redundant processing and storage. A `file_hash` column with a unique constraint was added to the `extractions` table.

### To Be Done (Next Steps):

*   ➡️ **Phase 3: Frontend avancé et gestion utilisateur**
    *   This is the next major part of the project. It involves creating a separate frontend application (e.g., using React) that will consume this backend API.
*   ➡️ **Phase 4: Upgrade to Production-Grade LLM (GPT-4o)**
    *   **Decision:** The final decision was made to pivot from free, unreliable Hugging Face models to the official OpenAI API using `gpt-4o`. This provides a massive leap in quality, reliability, and instruction-following capabilities.
    *   **Implementation:** The `llm_refiner.py` module was completely refactored to use the `openai` Python library. It now requires an `OPENAI_API_KEY` environment variable.
    *   **Prompt Engineering:** The system prompt for GPT-4o was significantly enhanced. It now explicitly instructs the model to perform cleaning (removing OCR artifacts, fixing typos) and reformulation (improving clarity) in addition to data extraction. This leverages the full power of the LLM to ensure the final JSON is clean and professional. This completes the core objective of Phase 4.
*   ➡️ **Phase 5: Templating and Final Document Generation**
    *   **Implementation:** A `Dossier_competences_OHA.docx` file was converted into a dynamic Jinja2 template (`cv_template.docx`). This was a manual process, verified by converting the `.docx` to `.xml` for review.
    *   A new `template_generator.py` module was created to handle rendering the template using the `docxtpl` library.
    *   The `/anonymize` endpoint was updated to use this new generator, completing the end-to-end pipeline from PDF upload to a fully formatted, anonymized `.docx` document.
*   ➡️ **Phase 6: Passage en production sécurisée**
    *   **Deployment:** Re-evaluate the deployment strategy for Render. This will likely involve creating a `build.sh` script to install Tesseract and Poppler in the build environment, or choosing a higher-tier plan with more memory.
    *   **CI/CD:** Set up a continuous integration and deployment pipeline (e.g., using GitHub Actions) to automate testing and deployments.
    *   **Security & Compliance:** Implement logging, data retention policies (e.g., auto-deleting CVs after 30 days), and other security measures to ensure GDPR compliance.

### Debugging & Reliability

*   **Template Debugging:** Implemented a crucial debugging feature for template creation. If the application is run in `DEBUG` mode (`DEBUG=True`) and a `TemplateSyntaxError` occurs during document generation, the system will automatically save the raw, pre-rendering XML of the template to `templates/debug_template.xml`. This allows developers to pinpoint the exact location of Jinja2 syntax errors within the `.docx` file's underlying XML structure, greatly simplifying the template debugging process.

### Feature: DOCX to Jinja2 Template Converter

*   **Objective:** Fulfill the user request to build a standalone tool for converting completed `.docx` CVs into `docxtpl`-compatible Jinja2 templates.
*   **Final Architecture (Multi-Stage LLM Pipeline):** After initial implementation, the feature was completely re-architected to ensure a deterministic and high-quality output, addressing issues with randomness and template correctness. The final pipeline now includes:
    *   **Stage 1 (LLM Semantic Analysis):** The system uses a powerful prompt to have an LLM generate a "semantic map" of the document, defining not only simple placeholder swaps but also complex, multi-paragraph blocks that should be replaced with Jinja2 `for` loops.
    *   **Stage 2 (Robust Annotation Engine):** A robust replacement engine was developed that can search for and replace multi-paragraph blocks of text across the entire document, including within tables. This was a critical fix to ensure the LLM's instructions could be applied correctly.
    *   **Stage 3 (LLM QA Review):** A new `template_qa.py` module was created to act as a final safety net. It uses a second, specialized LLM call to validate the generated template against a strict set of syntax and convention rules, guaranteeing that no invalid or broken templates are ever sent to the user.
*   **Frontend Enhancements:** The frontend was updated with functional JavaScript for drag-and-drop and to gracefully handle and display detailed error messages from the backend (e.g., from a failed QA review).
*   **Testing:** The test suite was updated to use `monkeypatch` to mock all external LLM calls, allowing for fast, deterministic, and cost-effective testing of the entire pipeline.
*   **Git Hygiene:**
    *   Resolved a merge conflict caused by a cached `__pycache__` file.
    *   Updated the `.gitignore` file to properly ignore `__pycache__` directories, preventing similar issues in the future.
