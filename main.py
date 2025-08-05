import logger_config # Import to configure logging
import logging
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env file.
load_dotenv(find_dotenv())

import os
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
import io

# Import the new, modularized components
from content_extractor import extract_json_from_cv
from template_builder import create_template_from_pdf
from renderer import render_html_to_pdf

# Get a logger for the current module
logger = logging.getLogger(__name__)

# --- Environment-based Configuration ---
DEBUG_MODE = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

# Initialize FastAPI app
app = FastAPI(
    title="CV Templating API",
    description="A robust, PDF/HTML-first API for creating and using professional CV templates.",
    version="2.0.0"
)

# --- API Endpoints for the New Architecture ---

@app.get("/", tags=["Status"])
def read_root():
    """Root endpoint to check if the API is running."""
    return {"message": "Welcome to the CV Templating API v2.0!"}

@app.post("/templates/create-from-pdf", tags=["Template Creation"])
async def create_template_from_pdf_endpoint(file: UploadFile = File(...)):
    """
    Workflow 1: Creates a new HTML/Jinja2 template from a user's styled PDF.

    This endpoint takes a PDF, uses a vision-capable LLM to convert it into
    high-fidelity HTML/CSS, and then programmatically prepares it as a reusable
    Jinja2 template. The template is not stored in this version but returned
    to the user for inspection.
    """
    logger.info(f"Received file '{file.filename}' for template creation.")
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    try:
        pdf_bytes = await file.read()
        pdf_stream = io.BytesIO(pdf_bytes)

        # Use the template_builder module to convert the PDF to a templated HTML string
        html_template_str = create_template_from_pdf(pdf_stream)

        # In a full implementation, we would save this string to a user's account in the DB.
        # For now, we return it directly for validation.
        logger.info("Successfully created HTML template from PDF.")

        headers = {'Content-Disposition': f'attachment; filename="generated_template_for_{file.filename.replace(".pdf", ".html")}"'}
        return StreamingResponse(
            io.BytesIO(html_template_str.encode('utf-8')),
            media_type="text/html",
            headers=headers
        )

    except (ValueError, HTTPException) as e:
        logger.error(f"Template creation failed: {e}", exc_info=DEBUG_MODE)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.critical(f"An unexpected error occurred during template creation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected server error occurred.")


@app.post("/cv/anonymize", tags=["CV Anonymization"])
async def anonymize_cv_with_template(
    template_name: str = Form("professional_template.html"),
    cv_file: UploadFile = File(...)
):
    """
    Workflow 2: Anonymizes a new CV using a specified HTML template.

    This endpoint extracts structured data from the uploaded CV, injects it
    into the specified HTML template, and returns the final, rendered PDF.
    """
    logger.info(f"Received CV '{cv_file.filename}' for anonymization with template '{template_name}'.")

    # Supported content types for CVs
    supported_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/png",
        "image/jpeg"
    ]
    if cv_file.content_type not in supported_types:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{cv_file.content_type}'.")

    try:
        cv_bytes = await cv_file.read()
        cv_stream = io.BytesIO(cv_bytes)

        # 1. Extract structured JSON from the CV
        json_data = extract_json_from_cv(cv_stream, cv_file.content_type)

        # 2. Render the specified HTML template with the extracted data into a PDF
        pdf_stream = render_html_to_pdf(template_name, json_data)

        # 3. Return the final PDF
        anonymized_filename = f"anonymized_{os.path.splitext(cv_file.filename)[0]}.pdf"
        headers = {'Content-Disposition': f'attachment; filename="{anonymized_filename}"'}

        return StreamingResponse(pdf_stream, media_type="application/pdf", headers=headers)

    except (ValueError, HTTPException) as e:
        logger.error(f"CV anonymization failed: {e}", exc_info=DEBUG_MODE)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.critical(f"An unexpected error occurred during CV anonymization: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected server error occurred.")
