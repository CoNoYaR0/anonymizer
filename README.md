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
-   # How to Use the CV Anonymizer Backend

Welcome! This guide will walk you through setting up, running, and deploying the CV Anonymizer backend application. This project is a FastAPI server designed to process CVs, extract personal information, and create anonymized versions.

## Table of Contents

1.  [Prerequisites](#prerequisites)
2.  [Local Setup](#local-setup)
3.  [Running the Application](#running-the-application)
4.  [Using the API](#using-the-api)
    *   [1. Uploading a CV (`/upload`)](#1-uploading-a-cv-upload)
    *   [2. Anonymizing a CV (`/anonymize`)](#2-anonymizing-a-cv-anonymize)
5.  [Deployment on Render](#deployment-on-render)
6.  [Configuration (Supabase)](#configuration-supabase)

---

## Prerequisites

Before you begin, make sure you have the following installed on your system:

*   **Python** (version 3.9 or higher)
*   **pip** (Python's package installer)

---

## Local Setup

Follow these steps to get the project running on your local machine.

### 1. Clone the Repository

If you haven't already, clone the project repository to your local machine:

```bash
git clone <repository-url>
cd cv-anonymizer-backend
```

### 2. Install Dependencies

This project uses several Python libraries. Install them using the `requirements.txt` file:

```bash
pip install -r requirements.txt
```
This will install FastAPI, Uvicorn, and all other necessary runtime packages for the application.

### 3. Set Up Environment Variables

The application uses [Supabase](https://supabase.com/) for storing uploaded CVs and the extracted data. You will need to create a `.env` file to store your Supabase credentials.

Create a file named `.env` in the root of the project directory and add the following lines:

```
SUPABASE_URL="YOUR_SUPABASE_URL"
SUPABASE_ANON_KEY="YOUR_SUPABASE_ANON_KEY"
OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
DEBUG="False"
```

*   **`SUPABASE_URL` / `SUPABASE_ANON_KEY`**: Your project's Supabase credentials.
*   **`OPENAI_API_KEY`**: Your API key from [platform.openai.com](https://platform.openai.com/). This is now required for the data refinement step, which uses the `gpt-4o` model.
*   **`DEBUG`**: Set to `"True"` to enable detailed debug logging and to receive detailed error messages in API responses. Defaults to `"False"`.

**Note:** If you run the application without this file, the Supabase integration will be disabled. The API will still work, but no files will be saved.

---

## Running the Application

Once you have completed the setup, you can run the application using `uvicorn`, which is a fast ASGI server.

```bash
uvicorn main:app --reload
```

This command starts the server. The `--reload` flag makes the server restart automatically when you make changes to the code.

You should see output similar to this, which means the server is running:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using statreload
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

The API is now available at `http://127.0.0.1:8000`.

---
## Monitoring the API

This project includes a live CLI dashboard to monitor the status of the API in real-time.

To run the dashboard, you will first need to install the development dependencies:
```bash
pip install -r dev-requirements.txt
```

Then, with the main FastAPI server running, open a separate terminal and run:

```bash
python monitor.py
```

This will display a panel that continuously updates with the server's CPU, memory, and disk usage. Press `Ctrl+C` to exit the monitor.

---

## Using the Application

The application provides two main functionalities: a web interface for converting `.docx` files into templates, and a REST API for the main CV anonymization pipeline.

### 1. DOCX to Jinja2 Template Converter (Web Interface)

This tool allows you to upload a completed `.docx` CV and get back a version with personal data automatically replaced by Jinja2 placeholders (e.g., `{{ name }}`).

*   **URL:** `http://127.0.0.1:8000/converter`

#### How to Use:
1.  Open the URL in your web browser.
2.  You will see a file upload form.
3.  Click to select your `.docx` CV or drag and drop it onto the form.
4.  Click the **"Convert and Download"** button.
5.  Your browser will automatically download the converted template file, which will be named something like `YourCV_template.docx`.

**Note:** The conversion process includes a final validation step to ensure the generated template is free of errors. If the system detects that it cannot safely create a template from your document, it will return an error message explaining the issue.

### 2. CV Anonymization API

You can interact with the API using tools like `curl`, Postman, or the interactive documentation.

#### API Documentation (Swagger UI)

FastAPI provides interactive API documentation for free. This is the easiest way to explore and test the API endpoints.

*   **URL:** `http://127.0.0.1:8000/docs`

Once you run the server, open this URL in your browser. You will see the Swagger UI, which allows you to see all the endpoints, their parameters, and test them directly from your browser.

#### API Endpoints

Here are the main endpoints:

#### 1. Get Server Status (`/status`)

This endpoint provides real-time information about the server's resource usage.

*   **URL:** `/status`
*   **Method:** `GET`

**Example using `curl`:**
```bash
curl http://127.0.0.1:8000/status
```

**Successful Response:**
```json
{
  "cpu_usage_percent": 15.4,
  "memory_usage": {
    "total": "31.27 GB",
    "available": "24.01 GB",
    "used": "7.26 GB",
    "percent": 23.2
  },
  "disk_usage": {
    "total": "475.22 GB",
    "used": "50.31 GB",
    "free": "424.91 GB",
    "percent": 10.6
  }
}
```

#### 2. Upload a CV & Start Anonymization (`/upload`)

This endpoint processes a PDF file, extracts all the data, saves it to the database, and returns a unique ID for the processed job.

*   **URL:** `/upload`
*   **Method:** `POST`
*   **Body:** `multipart/form-data` with a `file` field containing your PDF.

**Example using `curl`:**
```bash
curl -X POST -F "file=@/path/to/your/cv.pdf" http://127.0.0.1:8000/upload
```

**Successful Response:**

The API will return a JSON object containing the `extraction_id`. You will use this ID in the next step.
```json
{
  "extraction_id": 123
}
```

#### 3. Generate and Download the Anonymized CV (`/anonymize/{extraction_id}`)

This endpoint takes the `extraction_id` from the previous step, generates the anonymized `.docx` file, and provides a secure download link.

*   **URL:** `/anonymize/{extraction_id}` (e.g., `/anonymize/123`)
*   **Method:** `GET`

**Example using `curl`:**
```bash
curl http://127.0.0.1:8000/anonymize/123
```

**Successful Response:**

The response will contain a download link for the generated `.docx` file. This link is temporary and will expire after 24 hours.
```json
{
  "download_url": "https://<project-ref>.supabase.co/storage/v1/object/sign/cvs/anonymized_cvs/..."
}
```

---

## Deployment on Render

The `README.md` recommends [Render](https://render.com/) for deployment, which is a great choice for hosting FastAPI applications.

Here’s a step-by-step guide to deploy this backend on Render:

1.  **Create a New Web Service:**
    *   Go to your Render dashboard and click "New" -> "Web Service".
    *   Connect your GitHub account and select the `cv-anonymizer-backend` repository.

2.  **Configure the Service:**
    *   **Name:** Give your service a name (e.g., `cv-anonymizer-api`).
    *   **Region:** Choose a region close to you or your users.
    *   **Branch:** Select the main branch (`main` or `master`).
    *   **Runtime:** Render should automatically detect it as a Python app.
    *   **Build Command:** `pip install -r requirements.txt`
    *   **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
        *   `$PORT` is a variable that Render provides automatically.

3.  **Add Environment Variables:**
    *   Go to the "Environment" tab for your new service.
    *   Add the Supabase credentials you defined in your `.env` file:
        *   **Key:** `SUPABASE_URL`, **Value:** `YOUR_SUPABASE_URL`
        *   **Key:** `SUPABASE_KEY`, **Value:** `YOUR_SUPABASE_ANON_KEY`

4.  **Deploy:**
    *   Click "Create Web Service". Render will start building and deploying your application.
    *   Once deployed, you can access your API at the URL provided by Render.

---

## Configuration (Supabase)

To get your `SUPABASE_URL` and `SUPABASE_KEY` and set up the necessary storage and database, follow these steps.

### 1. Create a Supabase Project

*   Go to [supabase.com](https://supabase.com/) and create a new project.
*   Choose a name and database password, and select a region.

### 2. Get API Credentials

*   In your Supabase project dashboard, go to **Project Settings** (the gear icon).
*   Click on the **API** tab.
*   You will find your **Project URL** (`SUPABASE_URL`) and the `anon` `public` key (`SUPABASE_KEY`) here.

### 3. Create a Storage Bucket

*   Go to the **Storage** tab (the file icon).
*   Click **New bucket**.
*   Name the bucket `cvs`.
*   Make it a **public** bucket for now. You can configure more fine-grained access policies later.

### 4. Create a Database Table

*   Go to the **Table Editor** tab (the table icon).
*   Click **New table**.
*   Name the table `extractions`.
*   Uncheck "Enable Row Level Security (RLS)" for now to make it easier to get started.
*   Add the following columns:
    *   `id` (int8, Primary Key, auto-generated)
    *   `created_at` (timestamptz, auto-generated)
    *   `filename` (text)
    *   `storage_path` (text)
    *   `data` (jsonb)

Alternatively, you can go to the **SQL Editor**, create a **New query**, and run this SQL script to create the table:

```sql
CREATE TABLE public.extractions (
  id bigint NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  filename text NULL,
  storage_path text NULL,
  data jsonb NULL
);
ALTER TABLE public.extractions
  ADD CONSTRAINT extractions_pkey PRIMARY KEY (id);
-- This enables the auto-incrementing ID
CREATE SEQUENCE public.extractions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE public.extractions
    ALTER COLUMN id SET DEFAULT nextval('public.extractions_id_seq'::regclass);
```

Your backend is now fully configured to work with Supabase!

---

## Template Customization

The final anonymized document is generated from a `.docx` template located at `templates/cv_template.docx`. You can edit this file to change the layout, formatting, and content of the output.

### Template Variables

The template has access to the following variables:

- `initials` (str): The initials of the person's name.
- `title` (str): The person's title (e.g., "Software Engineer").
- `experience_years` (int): The total years of experience, calculated from the `period` of each experience.
- `current_company` (str): The company of the most recent experience.
- `experiences` (list of dicts): A list of work experiences. Each dictionary has the following keys:
    - `title` (str)
    - `company` (str)
    - `period` (str)
    - `description` (str)
    - `technologies` (list of str)
- `certifications` (list of dicts): A list of certifications. Each dictionary has:
    - `title` (str)
    - `year` (str)
    - `institution` (str)
- `skills` (dict): A dictionary where keys are skill categories (e.g., "frontend", "backend") and values are lists of skill names.
- `languages` (list of dicts): A list of languages. Each dictionary has:
    - `name` (str)
    - `level` (str)

### Debugging Template Errors

When you customize the `templates/cv_template.docx` file, you might accidentally introduce a syntax error in the Jinja2 templating language (e.g., `{{ variable }}` or `{% for item in items %}`). Finding these errors can be difficult because they are inside a `.docx` file.

This application includes a special debugging feature to help you.

#### How it Works

1.  **Enable Debug Mode**: In your `.env` file, make sure `DEBUG` is set to `"True"`.
    ```
    DEBUG="True"
    ```
2.  **Trigger the Error**: Run the application and make a request to the `/anonymize/{id}` endpoint that you know will fail due to the template error.
3.  **Check for the Debug File**: When the error occurs in debug mode, the server will automatically create a file at `templates/debug_template.xml`.
4.  **Inspect the File**: Open `debug_template.xml` in a code editor. This file contains the raw XML of your `.docx` template. You can now use your editor's search function (Ctrl+F) to find the exact line with the broken Jinja2 tag and fix it in your `.docx` template.

