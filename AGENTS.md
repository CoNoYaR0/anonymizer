# Agent Instructions for CV Anonymizer & Templating Engine

This document provides the strategic and technical blueprint for this project. Its purpose is to guide an AI software engineer (like Jules) through the architecture, data flows, and evolution of the system.

## 1. High-Level Objective

The project's primary goal is to provide a robust, automated pipeline for two distinct but related tasks:

1.  **CV Anonymization:** To process a candidate's CV (in any format), extract its content into a structured JSON format, and render it into a standardized, anonymized professional template.
2.  **Template Creation:** To allow a user to upload their own beautifully styled CV (as a PDF) and have the system automatically convert it into a reusable HTML/Jinja2 template that preserves the original look and feel.

The ultimate architecture is designed for scalability, reliability, and cost-effectiveness, prioritizing deterministic, programmatic control over unpredictable LLM outputs for structural tasks.

---

## 2. Core Architecture: The "PDF/HTML-First" Model

After a series of iterative developments, we have established that a "PDF/HTML-First" model is the optimal architecture. It avoids the fragility of direct `.docx` manipulation and leverages the strengths of web-native formats and modern LLMs.

The system is divided into two primary workflows:

### Workflow 1: Template Creation (The "Design" Phase)

This workflow allows a user to create a personal, reusable CV template from their existing, well-formatted PDF.

1.  **Input:** User uploads a high-quality, styled CV in **`.pdf`** format.
2.  **Stage 1: PDF-to-HTML Conversion (LLM Vision):**
    -   The PDF is sent to a multimodal LLM (like GPT-4o with vision capabilities).
    -   The LLM's task is to "re-create" the PDF's layout and content as clean, semantic **HTML and CSS**. This is a direct visual-to-code translation.
3.  **Stage 2: Templating (Jinja2 Injection):**
    -   The generated HTML is then parsed. The system programmatically replaces specific text content (e.g., the name "John Doe", the company "Example Corp") with the corresponding Jinja2 placeholders (e.g., `{{ name }}`, `{{ job.company }}`).
4.  **Stage 3: Validation & Storage (QA & Persistence):**
    -   The final HTML/Jinja2 template string is validated by a specialized QA LLM to ensure its correctness and quality.
    -   The validated template is saved to the database, associated with the user's account.
5.  **Output:** The user can preview their new template with sample data, rendered as a PDF. No `.docx` file is created in this workflow.

### Workflow 2: CV Anonymization (The "Usage" Phase)

This workflow is used to anonymize a new candidate's CV using a previously created template.

1.  **Input:** User uploads a candidate's CV in any common format (`.pdf`, `.docx`, `.png`, etc.).
2.  **Stage A: Content Extraction (OCR/Parsing):**
    -   The system uses the appropriate tool (`pytesseract` for images/PDFs, `python-docx` for text extraction) to get the raw text content from the document.
3.  **Stage B: Data Structuring (LLM Analysis):**
    -   The raw text is sent to an LLM. Its sole purpose is to perform Named Entity Recognition (NER) and data structuring, returning a clean, canonical **JSON object** containing the candidate's professional information (experiences, skills, etc.).
4.  **Stage C: Rendering:**
    -   The system retrieves the user's chosen HTML/Jinja2 template from the database.
    -   It renders the template, injecting the JSON data from Stage B.
5.  **Output:** The final document is delivered as a high-quality **PDF** (rendered via `WeasyPrint`) or as a raw **HTML string** for direct use in emails.

---

## 3. Architectural Evolution (Our Journey)

Understanding the "why" behind our architecture is critical. We did not start here. Our journey was an iterative process of identifying and solving fundamental problems.

### Initial Approach: Direct `.docx` Manipulation (`docxtpl`)

-   **Concept:** The initial idea was to treat the `.docx` file as the template itself. We used libraries like `python-docx` and `docxtpl` to directly find and replace text with Jinja2 placeholders.
-   **Challenges Encountered:**
    1.  **XML Fragility:** The `.docx` format is a complex archive of XML files. Minor changes by the user in Word could alter the XML structure in unexpected ways, breaking our text replacement logic.
    2.  **Uncontrollable Structure:** We had no programmatic control over the document's structure. This made it impossible to guarantee the correctness of injected Jinja2 loops (`{% for %}`...`{% endfor %}`).
    3.  **LLM Unreliability:** We relied on an LLM to generate the Jinja2 syntax. While powerful, the LLM would occasionally produce syntactically incorrect or incomplete blocks, which would break the `docxtpl` rendering engine.
    4.  **QA Complexity:** Validating the template required extracting all text and attempting to parse it, which was an imperfect simulation of the final render.

### Intermediate Solution: The Self-Correcting Loop

-   **Concept:** To combat the issues above, we built a highly sophisticated, multi-stage pipeline with a self-correcting feedback loop.
    -   **Deterministic Injection:** We shifted logic away from the LLM. Our Python code became responsible for generating *guaranteed-valid* Jinja2 blocks based on keywords.
    -   **QA-Driven Refinement:** A QA LLM would validate the generated template. If it failed, the list of issues was passed back to the start of the pipeline, and the LLM was prompted to "try again, fixing these specific errors."
-   **The Epiphany:** While this loop was powerful, it was ultimately a very complex and expensive (in terms of LLM tokens) solution to patch the fundamental problem: **`.docx` is not a suitable format for robust, programmatic templating.**

### Final Architecture: "PDF/HTML-First"

-   **Concept:** We decided to eliminate the root cause of the problem. By converting the user's styled document to HTML/CSS *once* and then using that as the template, we move the entire pipeline into a stable, web-native environment where we have 100% control.
-   **Benefits:** This model is faster, cheaper, more reliable, easier to debug, and produces a more professional and consistent final product (PDF/HTML). It represents the culmination of the lessons learned during our development journey.

---

## 4. Key Modules & Future State

To implement the new architecture, the roles of our existing files will be transformed:

-   `main.py`: Will continue to be the FastAPI orchestrator, but the endpoint logic will be rewritten to manage the new two-workflow system.
-   `docx_to_template_converter.py`: Will be heavily repurposed. The `_get_semantic_map_from_llm` will be adapted for the pure JSON extraction task (Workflow 2, Stage B). The complex deterministic and autofixing logic will be removed. New functions for PDF-to-HTML conversion will be added.
-   `template_qa.py`: Will be simplified. Its job will be to validate the generated HTML/Jinja2 template in Workflow 1.
-   `llm_refiner.py` & `template_generator.py`: These are part of a legacy workflow and will likely be deprecated or have their logic merged into the new system.
-   **New Dependencies:** `python-mammoth` (or `pypandoc`) for DOCX-to-HTML conversion and `WeasyPrint` for HTML-to-PDF rendering will be added.
