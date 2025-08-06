# CV Anonymizer & Templating Engine

This project provides a powerful backend service for processing, anonymizing, and templating CVs. It is designed to be a robust, scalable, and intelligent system that can handle various document formats and produce high-quality, professional outputs.

## Core Features

The application is built around two primary workflows:

1.  **CV Anonymization:** Takes a candidate's CV in any common format (PDF, DOCX, etc.), extracts its content into a structured JSON object, and renders it into a standardized, professional template.
2.  **Template Creation:** Allows a user to upload their own custom-styled CV in **`.docx`** format. The system uses the **Convertio API** to create a pixel-perfect HTML representation, which is then converted into a reusable HTML/Liquid template that preserves the original look and feel. This process is now optimized with a caching layer to avoid redundant API calls and uses a DOM-aware approach for template injection to ensure visual fidelity.

## Technical Architecture

The system is designed as a Python-based REST API using the **FastAPI** framework.

After significant iterative development, the project has adopted a **"Convertio-First"** architecture to ensure maximum reliability and deterministic output. This model uses the Convertio API for high-fidelity `DOCX-to-HTML` conversion, eliminating the unreliability of LLM-based visual analysis and guaranteeing that the final template is a perfect match for the user's original design.

For a complete and detailed explanation of the architecture, data flows, and the project's technical evolution, please see the definitive technical blueprint: **[AGENTS.md](AGENTS.md)**.

## Getting Started

To set up and run the project locally, please refer to the detailed setup and usage instructions in **[HOW_TO_USE.md](HOW_TO_USE.md)**.

This guide provides information on:
-   Prerequisites and dependencies (`CONVERTIO_API_KEY`)
-   Local setup and environment variables (`.env`)
-   Running the server
-   Using the API endpoints

## Tech Stack

-   **Backend:** FastAPI (Python)
-   **Document Conversion:** Convertio API (for DOCX-to-HTML)
-   **Data Extraction (from CVs):**
    -   `pytesseract` & `pdf2image` for OCR
    -   OpenAI GPT-4o for structured data extraction (JSON)
-   **Templating:** Liquid (via `liquid`) & OpenAI GPT-4o for placeholder injection
-   **Document Rendering:** WeasyPrint (for high-quality PDF output)
-   **Development:** `pytest` for testing
