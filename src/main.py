import os
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, RedirectResponse
from typing import Annotated
import io
import uuid

# Import the core logic modules
from . import template_builder
from . import content_extractor
from . import renderer
from . import database
from . import storage # Import the new storage module

# --- Constants ---
# Define bucket names for Supabase storage
TEMPLATE_BUCKET = "templates"
CV_BUCKET = "cvs"

# --- FastAPI App Initialization ---
app = FastAPI(
    title="CV Anonymizer & Templating Engine",
    description="A robust backend service for processing, anonymizing, and templating CVs.",
    version="1.1.0", # Version bump for storage integration
)

# --- Application Lifecycle Events ---
@app.on_event("startup")
def startup_event():
    print("FastAPI application started.")
    database.initialize_connection_pool()
    storage.initialize_supabase_client()

@app.on_event("shutdown")
def shutdown_event():
    if database.connection_pool:
        database.connection_pool.closeall()
        print("Database connection pool closed.")

# --- API Endpoints ---
@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "ok", "message": "CV Anonymizer API is running."}

@app.post("/templates/create-from-docx", tags=["Template Creation"])
async def create_template_endpoint(file: UploadFile = File(...)):
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .docx file.")

    try:
        file_content = await file.read()

        # Upload the original DOCX to Supabase storage for record-keeping
        file_extension = os.path.splitext(file.filename)[1]
        storage_path = f"uploads/{uuid.uuid4()}{file_extension}"
        storage.upload_file_to_storage(
            bucket_name=TEMPLATE_BUCKET,
            file_path=storage_path,
            file_content=file_content
        )

        # The template builder needs the file content, not the path
        # Note: We are passing the content directly now.
        liquid_template_str = template_builder.create_template_from_docx(file.filename, file_content)

        # Also upload the generated Liquid template to storage
        liquid_storage_path = f"generated/{uuid.uuid4()}.liquid.html"
        final_template_url = storage.upload_file_to_storage(
            bucket_name=TEMPLATE_BUCKET,
            file_path=liquid_storage_path,
            file_content=liquid_template_str.encode('utf-8')
        )

        # Return the public URL of the generated template
        return {"message": "Template created successfully", "template_url": final_template_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/cv/anonymize", tags=["CV Anonymization"])
async def anonymize_cv_endpoint(
    cv_file: Annotated[UploadFile, File(...)],
    template_name: Annotated[str, Form(...)],
):
    # In a production system, `template_name` would likely be a URL or an ID
    # that points to a template in our Supabase storage.
    # For now, we'll simulate downloading it.
    try:
        print(f"Attempting to use template: {template_name}")
        template_content_bytes = storage.download_file_from_storage(TEMPLATE_BUCKET, template_name)
        template_content = template_content_bytes.decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not find or download template '{template_name}'. Error: {e}")

    try:
        cv_content = await cv_file.read()

        # Upload CV to storage
        cv_storage_path = f"uploads/{uuid.uuid4()}_{cv_file.filename}"
        storage.upload_file_to_storage(CV_BUCKET, cv_storage_path, cv_content)

        # The content extractor needs the file content
        # TODO: Refactor content_extractor to accept bytes instead of a path.
        # For now, we save it temporarily to make the skeleton work.
        temp_cv_path = f"temp_{cv_file.filename}"
        with open(temp_cv_path, "wb") as f:
            f.write(cv_content)

        cv_data = content_extractor.extract_content_from_cv(temp_cv_path, cv_file.content_type)
        os.remove(temp_cv_path) # Clean up temp file

        # Render the final PDF
        pdf_bytes = renderer.render_cv_to_pdf(template_content, cv_data)

        # Upload the final PDF to storage
        pdf_storage_path = f"anonymized/{uuid.uuid4()}_anonymized_{cv_file.filename}.pdf"
        pdf_url = storage.upload_file_to_storage(CV_BUCKET, pdf_storage_path, pdf_bytes)

        # Redirect the user to the generated PDF
        return RedirectResponse(url=pdf_url)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
