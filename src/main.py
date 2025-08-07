import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import StreamingResponse, RedirectResponse, JSONResponse
from typing import Annotated
import io
import uuid

# Import the core logic modules
from . import template_builder
from . import content_extractor
from . import renderer
from . import database
from . import storage

# --- Constants ---
TEMPLATE_BUCKET = "templates"
CV_BUCKET = "cvs"

# --- FastAPI App Initialization ---
app = FastAPI(
    title="CV Anonymizer & Templating Engine",
    description="A robust backend service for processing, anonymizing, and templating CVs.",
    version="1.2.0", # Version bump for new workflow
)

# --- Lifecycle Events ---
@app.on_event("startup")
def startup_event():
    # ... (startup logic remains the same)
    pass

# --- API Endpoints ---
@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "ok", "message": "CV Anonymizer API is running."}

# --- Template Creation Workflow ---

@app.post("/templates/create-from-docx", tags=["Template Workflow"])
async def create_raw_html_from_docx(file: UploadFile = File(...)):
    """
    **Step 1: Convert DOCX to Raw HTML & Store It**

    This endpoint takes a `.docx` file, converts it to clean HTML using the
    Convertio API (or retrieves it from cache), and saves the raw HTML to
    Supabase storage. It returns the URL to this raw HTML file.
    """
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .docx file.")

    try:
        file_content = await file.read()

        # Get raw HTML (from cache or Convertio)
        raw_html = template_builder.convert_docx_to_html_and_cache(file_content)

        # Store the raw HTML in the bucket
        storage_path = f"raw_html/{uuid.uuid4()}.html"
        raw_html_url = storage.upload_file_to_storage(
            bucket_name=TEMPLATE_BUCKET,
            file_path=storage_path,
            file_content=raw_html.encode('utf-8')
        )

        return JSONResponse(
            status_code=200,
            content={
                "message": "Raw HTML created and stored successfully.",
                "raw_html_url": raw_html_url,
                "storage_path": storage_path
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@app.post("/templates/inject", tags=["Template Workflow"])
async def inject_placeholders_for_review(storage_path: str = Body(..., embed=True)):
    """
    **Step 2: Inject Liquid Placeholders for Review**

    Takes the path of a raw HTML file from storage, runs the AI injection
    process on it, and returns the resulting Liquid template for review.
    **This does not save the result.**
    """
    try:
        # Download the raw HTML from storage
        raw_html_bytes = storage.download_file_from_storage(TEMPLATE_BUCKET, storage_path)
        raw_html = raw_html_bytes.decode('utf-8')

        # Run the injection logic
        liquid_template = template_builder.inject_liquid_placeholders(raw_html)

        # Return the result as a string for the user to validate
        return JSONResponse(
            status_code=200,
            content={"liquid_template_preview": liquid_template}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@app.post("/templates/validate-and-save", tags=["Template Workflow"])
async def validate_and_save_template(
    storage_path: str = Body(...),
    validated_content: str = Body(...)
):
    """
    **Step 3: Validate and Save the Final Template**

    Once you have manually validated or corrected the Liquid template,
    send the final content here to **overwrite** the original raw HTML
    file in storage, making it the official, ready-to-use template.
    """
    try:
        # Overwrite the file in storage with the validated content
        final_url = storage.upload_file_to_storage(
            bucket_name=TEMPLATE_BUCKET,
            file_path=storage_path,
            file_content=validated_content.encode('utf-8')
        )

        return JSONResponse(
            status_code=200,
            content={
                "message": "Template validated and saved successfully.",
                "final_template_url": final_url
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


# --- CV Anonymization Workflow ---
# (This endpoint remains largely the same for now)
@app.post("/cv/anonymize", tags=["CV Anonymization"])
async def anonymize_cv_endpoint(
    cv_file: Annotated[UploadFile, File(...)],
    template_name: Annotated[str, Form(...)],
):
    # ... (implementation remains the same)
    pass
