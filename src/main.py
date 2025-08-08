import os
import logging
from logging.config import dictConfig
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import StreamingResponse, RedirectResponse, JSONResponse
from typing import Annotated
import io
import uuid

# --- Logging Configuration ---
log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "loggers": {
        "src": {  # This will catch logs from all modules in the 'src' package
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {  # Catch all other loggers, including uvicorn.access
        "handlers": ["console"],
        "level": "INFO",
    },
}
dictConfig(log_config)
# It's important to get the logger after the config is applied
logger = logging.getLogger(__name__)

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

@app.post("/templates/generate-from-docx", tags=["Template Workflow"])
async def generate_template_from_docx(file: UploadFile = File(...)):
    """
    **Unified Endpoint: DOCX to Final Template**

    This single endpoint orchestrates the entire template creation process:
    1.  Upload a `.docx` file.
    2.  The system converts it to HTML (using a cache for efficiency).
    3.  AI injects Liquid placeholders for dynamic content.
    4.  The final, ready-to-use template is saved to storage.
    5.  The public URL of the final template is returned.

    This replaces the previous three-step manual workflow.
    """
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .docx file.")

    try:
        file_content = await file.read()

        # Use the new unified function
        final_template_content = template_builder.create_and_inject_from_docx(file_content)

        # Save the final template to the specified storage path
        storage_path = f"generated/{uuid.uuid4()}.liquid.html"
        final_template_url = storage.upload_file_to_storage(
            bucket_name=TEMPLATE_BUCKET,
            file_path=storage_path,
            file_content=final_template_content.encode('utf-8')
        )

        return JSONResponse(
            status_code=200,
            content={
                "message": "Template generated and saved successfully.",
                "final_template_url": final_template_url,
                "storage_path": storage_path
            }
        )
    except Exception as e:
        # Log the exception for debugging
        logger.error(f"Error in /templates/generate-from-docx: {e}", exc_info=True)
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
