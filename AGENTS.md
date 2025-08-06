# Agent Instructions for CV Anonymizer & Templating Engine

This document provides the strategic and technical blueprint for this project. Its purpose is to guide an AI software engineer (like Jules) through the architecture, data flows, and evolution of the system.

## 1. High-Level Objective

The project's primary goal is to provide a robust, automated pipeline for two distinct but related tasks:

1.  **CV Anonymization:** To process a candidate's CV (in any format), extract its content into a structured JSON format, and render it into a standardized, anonymized professional template.
2.  **Template Creation:** To allow a user to upload their own beautifully styled CV **as a `.docx` file** and have the system automatically convert it into a reusable HTML/Liquid template that perfectly preserves the original look and feel.

The ultimate architecture is designed for scalability, reliability, and cost-effectiveness, prioritizing deterministic, programmatic control over unpredictable LLM outputs for structural tasks.

---

## 2. Core Architecture: The "Convertio-First" Model

After extensive iteration, we have established that a "Convertio-First" model is the optimal architecture. It is deterministic, reliable, and produces pixel-perfect results by leveraging a professional conversion service instead of relying on LLMs for visual interpretation.

The system is divided into two primary workflows:

### Workflow 1: Template Creation (The "Design" Phase)

This workflow allows a user to create a personal, reusable CV template from their existing, well-formatted `.docx` file.

1.  **Input:** User uploads a high-quality, styled CV in **`.docx`** format.
2.  **Caching:** The system calculates a SHA-256 hash of the uploaded file and checks a database cache. If a previously converted HTML for this exact file exists, it skips the conversion step and uses the cached version.
3.  **Stage 1: DOCX-to-HTML Conversion (Convertio API):**
    -   If the file is not in the cache, the `.docx` file is sent to the **Convertio API**.
    -   Convertio performs a high-fidelity conversion, returning a single HTML file with all styling inlined. This process is deterministic and visually exact.
    -   The newly converted HTML is then stored in the cache for future use.
4.  **Stage 2: Templating (Liquid Injection):**
    -   The clean, structured HTML is then passed to an LLM (e.g., GPT-4o).
    -   The LLM's *only* task is to intelligently identify and replace the static text content (e.g., the name "John Doe") with the corresponding Liquid placeholders (e.g., `{{ name }}`).
    -   This process is now DOM-aware, using `BeautifulSoup` to parse the HTML and replace text nodes, ensuring that the visual fidelity of the template is preserved.
5.  **Stage 3: Validation & Storage:**
    -   The final HTML/Liquid template string is validated programmatically using the `liquid` library to ensure its syntax is correct.
    -   The validated template is ready to be saved and associated with a user's account.
6.  **Output:** A reusable, syntactically valid `template.liquid.html` file that perfectly matches the user's original branding and layout.

### Workflow 2: CV Anonymization (The "Usage" Phase)

This workflow remains unchanged. It is used to anonymize a new candidate's CV using a previously created template.

1.  **Input:** User uploads a candidate's CV in any common format (`.pdf`, `.docx`, `.png`, etc.).
2.  **Stage A: Content Extraction (OCR/Parsing):**
    -   The system uses the appropriate tool (`pytesseract` for images/PDFs, `python-docx` for text extraction) to get the raw text content.
3.  **Stage B: Data Structuring (LLM Analysis):**
    -   The raw text is sent to an LLM to return a clean, canonical **JSON object** of the candidate's professional information.
4.  **Stage C: Rendering:**
    -   The system retrieves the user's chosen HTML/Liquid template.
    -   It renders the template using `liquid`, injecting the JSON data from Stage B.
5.  **Output:** The final document is delivered as a high-quality **PDF** (rendered via `WeasyPrint`) or as a raw HTML string.

---

## 3. Architectural Evolution (Our Journey)

Understanding the "why" behind our architecture is critical.

### Initial Approach: Direct `.docx` Manipulation
-   **Concept:** The initial idea was to treat the `.docx` file itself as a template using `docxtpl`.
-   **Problem:** This was extremely fragile due to the complexity of the underlying XML and the unreliability of LLM-generated Jinja2 syntax.

### Intermediate Solution: "PDF/HTML-First"
-   **Concept:** To escape the fragility of `.docx`, we pivoted to converting a styled PDF into HTML using a vision-capable LLM.
-   **Problem:** While an improvement, this approach suffered from its own form of unreliability. The LLM would often "hallucinate" layouts, miss sections, or fail to replicate the design with pixel-perfect accuracy. The process was not deterministic.

### Final Architecture: "Convertio-First"
-   **Concept:** We decided to eliminate the root cause of the problem: using an LLM for structural conversion. By using a professional, deterministic service (**Convertio**) to handle the DOCX-to-HTML conversion, we get a perfect, reliable HTML representation every time.
-   **Benefits:** This model is the final, most robust version of the system. It is fast, 100% reliable, and produces a pixel-perfect template that matches the user's original document. The LLM is now only used for the task it excels at: language-based content replacement, not visual design.

---

## 4. Key Modules & Final State

-   `main.py`: The FastAPI orchestrator. The template creation endpoint is now `/templates/create-from-docx` and accepts `.docx` files.
-   `template_builder.py`: This module has been completely refactored. It no longer uses LLMs for HTML generation. Instead, it contains the logic to call the Convertio API, poll for results, download the converted HTML, and then orchestrate the Liquid injection via a separate LLM call. It also includes the caching logic and the DOM-aware template injection.
-   `content_extractor.py`: Unchanged. Continues to handle parsing of incoming candidate CVs.
-   `renderer.py`: Unchanged. Continues to render the final HTML/Liquid template into a PDF using `WeasyPrint`.
-   **Legacy Files:** All files related to the old `.docx` and PDF-to-HTML workflows (e.g., `docx_to_template_converter.py`, `llm_refiner.py`, etc.) have been deleted.
-   **Dependencies:** `httpx` is used for the Convertio API calls. `liquid` is the standard templating engine. `WeasyPrint` is the PDF renderer.
