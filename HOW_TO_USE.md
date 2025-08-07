# How to Use the CV Anonymizer & Templating Engine

This guide will walk you through setting up and running the CV Anonymizer backend application. This project is a FastAPI server designed to create professional CV templates and use them to anonymize candidate CVs, using Supabase for all backend services.

## Table of Contents

1.  [Prerequisites](#prerequisites)
2.  [Local Setup](#local-setup)
3.  [Running the Application](#running-the-application)
4.  [Using the API](#using-the-api)

---

## Prerequisites

Before you begin, make sure you have the following installed on your system:

*   **Python** (version 3.9 or higher)
*   **pip** (Python's package installer)
*   **Poppler**: This is required for PDF processing.
*   **Tesseract**: This is required for OCR (extracting text from images).

---

## Local Setup

Follow these steps to get the project running on your local machine.

### 1. Clone the Repository and Install Dependencies

```bash
git clone <repository-url>
cd cv-anonymizer-backend
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a file named `.env` in the root of the project directory by copying the `.env.example` file. Then, fill in your credentials.

**To find your Supabase credentials:**

*   **`SUPABASE_URL` & `SUPABASE_ANON_KEY`**: Go to **Project Settings > API** in your Supabase dashboard.
*   **`DB_PASSWORD`**: The database password you set when creating your Supabase project.
*   **`DB_HOST`**: This is the most critical step for a stable connection.
    1.  Go to **Project Settings > Database**.
    2.  Scroll down to the **Connection pool** section.
    3.  Ensure you are on the **Session mode** tab.
    4.  Copy the host from the connection string (the part that looks like `aws-0-xx-xxxx-x.pooler.supabase.com`).
    5.  Paste this value into the `DB_HOST` field in your `.env` file.

Your `.env` file should look like this:
```
# --- Third-Party APIs ---
CONVERTIO_API_KEY="YOUR_CONVERTIO_API_KEY"
OPENAI_API_KEY="YOUR_OPENAI_API_KEY"

# --- Supabase Configuration ---
SUPABASE_URL="https://your-project-id.supabase.co"
SUPABASE_ANON_KEY="your-supabase-anon-key"
DB_PASSWORD="your-supabase-db-password"
PROJECT_NAME="your-supabase-project-name"
DB_HOST="aws-0-your-region.pooler.supabase.com" # Copied from your dashboard

# --- Application Settings ---
DEBUG="False"
```

### 3. Run Database Migrations
Before the first run, set up the database schema:
```bash
python apply_migrations.py
```
If this command runs successfully, your database is connected correctly.

### 4. Create Storage Buckets
Go to the **Storage** section in your Supabase dashboard and create two **public** buckets:
1.  `templates`
2.  `cvs`

---

## Running the Application

Once you have completed the setup, you can run the application using `uvicorn`:

```bash
uvicorn src.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

---

## Using the API
(API usage details remain the same)
...
