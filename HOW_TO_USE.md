# How to Use the CV Anonymizer Backend

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
This will install FastAPI, Uvicorn, EasyOCR, spaCy, and all other necessary packages. The first time you run this, it might take a while as it needs to download machine learning models.

### 3. Set Up Environment Variables

The application uses [Supabase](https://supabase.com/) for storing uploaded CVs and the extracted data. You will need to create a `.env` file to store your Supabase credentials.

Create a file named `.env` in the root of the project directory and add the following lines:

```
SUPABASE_URL="YOUR_SUPABASE_URL"
SUPABASE_KEY="YOUR_SUPABASE_ANON_KEY"
```

Replace `"YOUR_SUPABASE_URL"` and `"YOUR_SUPABASE_ANON_KEY"` with your actual Supabase project URL and public anon key. See the [Configuration (Supabase)](#configuration-supabase) section for details on how to get these.

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

## Using the API

You can interact with the API using tools like `curl` or Postman. Here are the two main endpoints:

### 1. Uploading a CV (`/upload`)

This endpoint processes a PDF file, extracts the text, and identifies personal information.

*   **URL:** `/upload`
*   **Method:** `POST`
*   **Body:** `multipart/form-data` with a `file` field containing the PDF.

**Example using `curl`:**

```bash
curl -X POST -F "file=@/path/to/your/cv.pdf" http://127.0.0.1:8000/upload
```

**Successful Response:**

The API will return a JSON object containing the extracted text and entities. You should save this response, as you will need it for the next step.

```json
{
  "filename": "cv.pdf",
  "entities": {
    "persons": ["John Doe"],
    "locations": ["New York"],
    "emails": ["john.doe@email.com"],
    "phones": ["123-456-7890"],
    "skills": [],
    "experience": []
  },
  "raw_text": "John Doe\\nNew York\\njohn.doe@email.com\\n123-456-7890..."
}
```

### 2. Anonymizing a CV (`/anonymize`)

This endpoint takes the JSON data from the `/upload` step, creates an anonymized version, and generates a `.docx` file.

*   **URL:** `/anonymize`
*   **Method:** `POST`
*   **Body:** The JSON response you received from the `/upload` endpoint.

**Example using `curl`:**

First, save the output of the `/upload` call to a file (e.g., `response.json`). Then, use that file as the data for this request:

```bash
curl -X POST -H "Content-Type: application/json" -d @response.json http://127.0.0.1:8000/anonymize
```

**Successful Response:**

If Supabase is configured, the response will contain a download link for the anonymized `.docx` file.

```json
{
  "download_url": "https://<project-ref>.supabase.co/storage/v1/object/sign/cvs/anonymized_cvs/..."
}
```

If Supabase is not configured, it will return the anonymized text directly:

```json
{
  "message": "Anonymized document generated, but Supabase is not configured for upload.",
  "anonymized_text": "Person (JD)\\n[LOCATION REDACTED]\\n[EMAIL REDACTED]\\n[PHONE REDACTED]..."
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
