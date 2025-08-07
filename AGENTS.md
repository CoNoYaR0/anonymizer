# Agent Instructions for CV Anonymizer & Templating Engine

---
## ⚠️ Core Directives ⚠️
### **1. NO ASSUMPTIONS. VERIFY EVERYTHING.**
- **This is the most important rule.** Do not assume how a library works, what a variable contains, or how a configuration is structured.
- **You MUST verify all external factors.** This includes:
    - Reading the documentation for third-party library functions and their expected exceptions.
    - Checking environment variables and handling cases where they might be missing.
    - Directly testing functionality in isolation if its behavior is not 100% certain.
- **Guessing is not permitted.** A wrong assumption can lead to critical failures. The time spent verifying is always less than the time spent fixing a bug caused by a guess.
---

This document provides the strategic and technical blueprint for this project. Its purpose is to guide an AI software engineer (like Jules) through the architecture, data flows, and evolution of the system.

## 1. High-Level Objective

The project's primary goal is to provide a robust, automated pipeline for two distinct but related tasks:

1.  **CV Anonymization:** To process a candidate's CV (in any format), extract its content into a structured JSON format, and render it into a standardized, anonymized professional template.
2.  **Template Creation:** To allow a user to upload their own beautifully styled CV **as a `.docx` file** and have the system automatically convert it into a reusable HTML/Liquid template that perfectly preserves the original look and feel.

The architecture is designed for scalability, reliability, and cost-effectiveness, prioritizing deterministic, programmatic control over unpredictable LLM outputs for structural tasks.

---

## 2. Core Architecture: The "Convertio-First" Model

The "Convertio-First" model is the optimal architecture. It is deterministic, reliable, and produces pixel-perfect results by leveraging a professional conversion service.

### Workflow 1: Template Creation (The "Design" Phase)

1.  **Input:** User uploads a high-quality, styled CV in **`.docx`** format.
2.  **Caching:** The system calculates a SHA-256 hash of the uploaded file and **checks a PostgreSQL database cache**. If a previously converted HTML for this exact file exists, it skips the conversion step and uses the cached version, ensuring efficiency and reducing cost.
3.  **Stage 1: DOCX-to-HTML Conversion (Convertio API):**
    -   If the file is not in the cache, the `.docx` file is sent to the **Convertio API**.
    -   The newly converted HTML is then **stored in the database cache** for future use.
4.  **Stage 2: Templating (Liquid Injection):**
    -   The clean, structured HTML is passed to an LLM (GPT-4o) to intelligently identify and replace static text with Liquid placeholders (e.g., `{{ name }}`).
    -   This process uses `BeautifulSoup` to parse the DOM and replace text nodes, ensuring the HTML structure is not broken.
5.  **Stage 3: Validation & Storage:**
    -   The final HTML/Liquid template is validated programmatically.
6.  **Output:** A reusable, syntactically valid `template.liquid.html` file.

### Workflow 2: CV Anonymization (The "Usage" Phase)

This workflow is used to anonymize a new candidate's CV using a pre-existing template.

1.  **Input:** User uploads a candidate's CV (`.pdf`, `.docx`, `.png`, etc.).
2.  **Stage A: Content Extraction (OCR/Parsing):**
    -   The system uses `pytesseract` (for images/PDFs) or `python-docx` to get the raw text. **Note: OCR is currently configured for French (`fra`).**
3.  **Stage B: Data Structuring (LLM Analysis):**
    -   The raw text is sent to an LLM to return a clean, canonical **JSON object**.
4.  **Stage C: Rendering:**
    -   The system renders the chosen HTML/Liquid template with the JSON data into a high-quality **PDF** using `WeasyPrint`.

---

## 3. Setup & Configuration

To run this project, you must configure the following environment variables (e.g., in a `.env` file):

-   `DB_URL`: The full PostgreSQL connection string for the database. This is required for the caching mechanism.
    -   Example: `postgresql://user:password@host:port/database`
-   `CONVERTIO_API_KEY`: Your API key for the Convertio service. This is required for the template creation workflow.
-   `OPENAI_API_KEY`: Your API key for OpenAI, used for all LLM-based processing.

**Database Migrations:**
Before running the application for the first time, you must apply the database migrations. The `apply_migrations.py` script is provided for this purpose. It will connect to the database specified in `DB_URL` and create the necessary tables.

```bash
# Ensure psycopg2-binary is installed
pip install psycopg2-binary

# Run the migration script
python apply_migrations.py
```

---

## 4. Key Modules & Current State

-   `main.py`: The FastAPI orchestrator.
-   `database.py`: **New module.** Manages the connection pool to the PostgreSQL database.
-   `template_builder.py`: Implements the "Template Creation" workflow. It now connects to the database for caching and relies solely on the `CONVERTIO_API_KEY` environment variable.
-   `content_extractor.py`: Unchanged. Handles parsing of incoming candidate CVs.
-   `renderer.py`: Unchanged. Renders the final PDF.
-   `apply_migrations.py`: **New script.** A utility to set up the database schema.
-   **Dependencies:** `psycopg2-binary` has been added for database connectivity.
