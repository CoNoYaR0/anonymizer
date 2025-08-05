# CV Anonymizer & Templating Engine

This project provides a powerful backend service for processing, anonymizing, and templating CVs. It is designed to be a robust, scalable, and intelligent system that can handle various document formats and produce high-quality, professional outputs.

## Core Features

The application is built around two primary workflows:

1.  **CV Anonymization:** Takes a candidate's CV in any common format (PDF, DOCX, etc.), extracts its content into a structured JSON object, and renders it into a standardized, professional template. This is ideal for recruitment agencies and consulting firms who need to present candidates to clients in a consistent and anonymized format.

2.  **Template Creation:** Allows a user to upload their own custom-styled CV in PDF format. The system analyzes the layout and creates a reusable HTML/Jinja2 template that preserves the original look and feel. This allows users to maintain their personal or corporate branding across all anonymized CVs.

## Technical Architecture

The system is designed as a Python-based REST API using the **FastAPI** framework.

After significant iterative development, the project has adopted a **"PDF/HTML-First"** architecture to ensure maximum reliability, control, and quality. This approach avoids the fragility of direct `.docx` manipulation in favor of more stable, web-native formats.

For a complete and detailed explanation of the architecture, data flows, and the project's technical evolution, please see the definitive technical blueprint: **[AGENTS.md](AGENTS.md)**.

## Getting Started

To set up and run the project locally, please refer to the detailed setup and usage instructions in **[HOW_TO_USE.md](HOW_TO_USE.md)**.

This guide provides information on:
-   Prerequisites and dependencies
-   Local setup and environment variables (`.env`)
-   Running the server
-   Using the API endpoints

## Tech Stack

-   **Backend:** FastAPI (Python)
-   **Data Extraction:**
    -   `pytesseract` & `pdf2image` for OCR
    -   OpenAI GPT-4o for structured data extraction (JSON) and visual analysis (PDF-to-HTML)
-   **Templating:** Jinja2
-   **Document Rendering:** WeasyPrint (for high-quality PDF output)
-   **Database & Storage:** Supabase (Postgres, S3-compatible storage)
-   **Development:** `pytest` for testing, `rich` for monitoring scripts
