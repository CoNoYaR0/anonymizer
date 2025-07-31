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
*   ✅ **API Monitoring:** A `/status` endpoint provides resource metrics.
*   ✅ **API Documentation:** Interactive documentation is automatically available.

### To Be Done (Next Steps):

*   ➡️ **Phase 3: Frontend avancé et gestion utilisateur**
    *   This is the next major part of the project. It involves creating a separate frontend application (e.g., using React) that will consume this backend API.
*   ➡️ **Phase 4: Intégration d’un LLM open-source**
    *   This is a planned enhancement for the backend. The goal is to use a Large Language Model (like Mistral, as suggested in the `README.md`) to significantly improve the accuracy and structure of the extracted data (e.g., correctly parsing job missions, skills, and experiences). This will address the remaining inaccuracies of the current spaCy-based extraction.
*   ➡️ **Phase 5: Passage en production sécurisée**
    *   **Deployment:** Re-evaluate the deployment strategy for Render. This will likely involve creating a `build.sh` script to install Tesseract and Poppler in the build environment, or choosing a higher-tier plan with more memory.
    *   **CI/CD:** Set up a continuous integration and deployment pipeline (e.g., using GitHub Actions) to automate testing and deployments.
    *   **Security & Compliance:** Implement logging, data retention policies (e.g., auto-deleting CVs after 30 days), and other security measures to ensure GDPR compliance.
