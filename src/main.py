import os
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from typing import Annotated
import io

# Import the core logic modules
from . import template_builder
from . import content_extractor
from . import renderer
from . import database

# --- FastAPI App Initialization ---

app = FastAPI(
    title="CV Anonymizer & Templating Engine",
    description="A robust backend service for processing, anonymizing, and templating CVs.",
    version="1.0.0",
)

# --- Application Lifecycle Events ---

@app.on_event("startup")
def startup_event():
    """
    Actions to perform on application startup.
    - Initializes the database connection pool.
    """
    # NOTE: The database module already initializes this when loaded.
    # In a more complex setup, we might explicitly control initialization here.
    print("FastAPI application started.")
    if database.connection_pool is None:
        print("Database pool was not initialized on module load, initializing now.")
        database.initialize_connection_pool()

@app.on_event("shutdown")
def shutdown_event():
    """
    Actions to perform on application shutdown.
    - Closes the database connection pool.
    """
    if database.connection_pool:
        database.connection_pool.closeall()
        print("Database connection pool closed.")

# --- API Endpoints ---

@app.get("/", tags=["Health Check"])
def read_root():
    """
    Root endpoint for basic health checks.
    """
    return {"status": "ok", "message": "CV Anonymizer API is running."}


@app.post("/templates/create-from-docx", tags=["Template Creation"])
async def create_template_endpoint(file: UploadFile = File(...)):
    """
    **Workflow 1: Create a Template from a DOCX file.**

    This endpoint takes a styled `.docx` file, converts it to high-fidelity
    HTML using the Convertio API, and then injects Liquid placeholders to
    create a reusable template.
    """
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .docx file.")

    try:
        # Save the uploaded file temporarily to pass its path to modules
        # In a production system, this would be handled more robustly (e.g., in-memory or a temp dir)
        temp_file_path = f"temp_{file.filename}"
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_content = await file.read()
        await file.seek(0) # Reset file pointer after reading

        # TODO: Call the template_builder module to orchestrate the creation.
        # This will handle caching, Convertio conversion, and LLM placeholder injection.
        print("Calling template_builder to create template...")
        liquid_template_str = template_builder.create_template_from_docx(temp_file_path, file_content)

        # Return the resulting template as a downloadable HTML file.
        return StreamingResponse(
            io.BytesIO(liquid_template_str.encode()),
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename=generated_template.liquid.html"}
        )

    except Exception as e:
        # TODO: Add more specific error handling
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@app.post("/cv/anonymize", tags=["CV Anonymization"])
async def anonymize_cv_endpoint(
    cv_file: Annotated[UploadFile, File(...)],
    template_name: Annotated[str, Form(...)],
):
    """
    **Workflow 2: Anonymize a CV with a Template.**

    This endpoint takes a candidate's CV, extracts its content into a
    structured JSON object, and renders it into a final PDF using a
    specified template.
    """
    # For the skeleton, we assume templates are stored in a `templates/` directory
    template_path = os.path.join("templates", template_name)
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found.")

    try:
        # Save the uploaded CV file temporarily
        temp_cv_path = f"temp_{cv_file.filename}"
        with open(temp_cv_path, "wb") as buffer:
            shutil.copyfileobj(cv_file.file, buffer)

        # 1. Extract structured content from the CV
        print("Calling content_extractor to get structured data from CV...")
        cv_data = content_extractor.extract_content_from_cv(temp_cv_path, cv_file.content_type)

        # 2. Load the specified HTML/Liquid template
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        # 3. Render the template with the data to produce a PDF
        print("Calling renderer to generate the final PDF...")
        pdf_bytes = renderer.render_cv_to_pdf(template_content, cv_data)

        # 4. Return the generated PDF as a downloadable file
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=anonymized_{cv_file.filename}.pdf"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_cv_path):
            os.remove(temp_cv_path)
