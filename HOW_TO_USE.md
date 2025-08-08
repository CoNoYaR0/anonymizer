# How to Use the CV Anonymizer & Templating Engine

This guide will walk you through setting up and running the CV Anonymizer backend application. This project is a FastAPI server designed to create professional CV templates and use them to anonymize candidate CVs, using Supabase for all backend services.

## Table of Contents

1.  [Prerequisites](#prerequisites)
2.  [Local Setup](#local-setup)
3.  [Running the Application](#running-the-application)
4.  [Using the API](#using-the-api)

---

## Prerequisites

(Prerequisites section remains the same)
...

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

*   **Storage Credentials (Project Settings > API):**
    *   `SUPABASE_URL`
    *   `SUPABASE_ANON_KEY`

*   **Database Credentials (Project Settings > Database > Connection pool):**
    1.  Make sure you are on the **Session mode** tab.
    2.  Copy the following values directly from the connection string details:
        *   `DB_HOST` (e.g., `aws-0-xx-xxxx-x.pooler.supabase.com`)
        *   `DB_USER` (e.g., `postgres.yourprojectref`)
        *   `DB_PASSWORD` (This is the password you set for your database).

Your `.env` file should look like this:
```
# --- Third-Party APIs ---
CONVERTIO_API_KEY="YOUR_CONVERTIO_API_KEY"
OPENAI_API_KEY="YOUR_OPENAI_API_KEY"

# --- Supabase Configuration ---
SUPABASE_URL="..."
SUPABASE_ANON_KEY="..."
PROJECT_NAME="anonymizer"

DB_HOST="..."
DB_USER="..."
DB_PASSWORD="..."

# --- Application Settings ---
# Set to "True" to enable verbose DEBUG-level logging for development.
# Set to "False" for quieter INFO-level logging in production.
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

Once your environment is configured, you can run the FastAPI server using Uvicorn, which is included in the project's dependencies.

From the root of the project directory, run the following command:

```bash
uvicorn src.main:app --reload
```

This command will start the development server.
-   `src.main:app` tells Uvicorn where to find the FastAPI application instance (`app` in `src/main.py`).
-   `--reload` enables hot-reloading, so the server will automatically restart when you make changes to the code.

You should see output in your console indicating that the server is running, along with logs for any incoming requests or application processes. This will help you monitor the application's activity in real-time.

The API will be available at `http://127.0.0.1:8000`.

---

## Using the API
(This section remains the same)
...
