# How to Use the CV Anonymizer & Templating Engine

This guide will walk you through setting up and running the CV Anonymizer backend application. This project is a FastAPI server designed to create professional CV templates and use them to anonymize candidate CVs, using Supabase for all backend services.

## Table of Contents

1.  [Prerequisites](#prerequisites)
2.  [Local Setup](#local-setup)
3.  [Running the Application](#running-the-application)
4.  [Using the API](#using-the-api)
    *   [Workflow 1: Create a Template from a DOCX](#workflow-1-create-a-template-from-a-docx)
    *   [Workflow 2: Anonymize a CV with a Template](#workflow-2-anonymize-a-cv-with-a-template)

---

## Prerequisites

Before you begin, make sure you have the following installed on your system:

*   **Python** (version 3.9 or higher)
*   **pip** (Python's package installer)
*   **Poppler**: This is required for PDF processing.
    *   **On macOS (using Homebrew):** `brew install poppler`
    *   **On Debian/Ubuntu:** `sudo apt-get install poppler-utils`
*   **Tesseract**: This is required for OCR (extracting text from images).
    *   **On macOS (using Homebrew):** `brew install tesseract`
    *   **On Debian/Ubuntu:** `sudo apt-get install tesseract-ocr`

---

## Local Setup

Follow these steps to get the project running on your local machine.

### 1. Clone the Repository

```bash
git clone <repository-url>
cd cv-anonymizer-backend
```

### 2. Install Dependencies

Install the required Python libraries using `pip`:

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a file named `.env` in the root of the project directory by copying the `.env.example` file. Then, fill in your credentials.

```
# --- Third-Party APIs ---
CONVERTIO_API_KEY="YOUR_CONVERTIO_API_KEY"
OPENAI_API_KEY="YOUR_OPENAI_API_KEY"

# --- Supabase Configuration ---
SUPABASE_URL="https://your-project-id.supabase.co"
SUPABASE_ANON_KEY="your-supabase-anon-key"
DB_PASSWORD="your-supabase-db-password"
PROJECT_NAME="your-supabase-project-name"
DB_HOST="aws-0-your-region.pooler.supabase.com"

# --- Application Settings ---
DEBUG="False"
```

*   **`CONVERTIO_API_KEY`**: Your API key from [convertio.co/api/](https://convertio.co/api/).
*   **`OPENAI_API_KEY`**: Your API key from [platform.openai.com](https://platform.openai.com/).
*   **`SUPABASE_URL` & `SUPABASE_ANON_KEY`**: Found in your Supabase project's API settings.
*   **`DB_PASSWORD`**: The database password you set when creating your Supabase project.
*   **`PROJECT_NAME`**: A name for your project, used for organizing storage buckets (e.g., "anonymizer").
*   **`DB_HOST`**: The **Connection Pooler** host for your database. You can find this in your Supabase project's Database settings. Using the pooler is required for IPv4 compatibility.

### 4. Run Database Migrations
Before the first run, set up the database schema:
```bash
python apply_migrations.py
```

---

## Running the Application

Once you have completed the setup, you can run the application using `uvicorn`:

```bash
uvicorn src.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

---

## Using the API

The easiest way to explore the endpoints is through the interactive Swagger UI at `http://127.0.0.1:8000/docs`.

### Workflow 1: Create a Template from a DOCX

This endpoint converts a `.docx` file into a reusable HTML/Liquid template and stores it in Supabase Storage.

*   **URL:** `/templates/create-from-docx`
*   **Method:** `POST`
*   **Body:** `multipart/form-data` with a `file` field.

**Example using `curl`:**
```bash
curl -X POST -F "file=@/path/to/your/template.docx" http://127.0.0.1:8000/templates/create-from-docx
```

**Successful Response:**
The API will return a JSON object with a link to the generated template in Supabase Storage.
```json
{
  "message": "Template created successfully",
  "template_url": "https://<...>.supabase.co/storage/v1/object/public/templates/generated/<...>.liquid.html"
}
```

### Workflow 2: Anonymize a CV with a Template

This endpoint anonymizes a CV and renders it into a PDF using a specified template from storage.

*   **URL:** `/cv/anonymize`
*   **Method:** `POST`
*   **Body:** `multipart/form-data` with two fields:
    1.  `cv_file`: The candidate's CV file (`.pdf`, `.docx`, etc.).
    2.  `template_name`: The **path** of the template file in Supabase storage (e.g., `generated/your-template.liquid.html`).

**Example using `curl`:**
```bash
curl -X POST \
  -F "cv_file=@/path/to/candidate_cv.pdf" \
  -F "template_name=generated/your-template.liquid.html" \
  http://127.0.0.1:8000/cv/anonymize -L
```
**Note:** Use the `-L` flag with `curl` to follow the redirect.

**Successful Response:**
The API will respond with a **307 Temporary Redirect** to the final, anonymized PDF stored in Supabase. Your browser or client will automatically download the file from this URL.
