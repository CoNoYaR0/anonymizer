import os
import re
import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from pydantic import BaseModel, Field
import os
import pytesseract
from pdf2image import convert_from_bytes
import spacy
from supabase import create_client, Client
import io
from dotenv import load_dotenv
from PIL import Image
import docx
from docx.shared import Inches
import psutil
from llm_refiner import refine_extraction_with_llm

# Load environment variables from .env file
load_dotenv()


class ExtractedEntities(BaseModel):
    persons: list[str] = Field(..., example=["Jean Dupont"])
    locations: list[str] = Field(..., example=["Paris"])
    emails: list[str] = Field(..., example=["jean.dupont@example.com"])
    phones: list[str] = Field(..., example=["01 23 45 67 89"])
    skills: list[str] = Field(..., example=["Python", "FastAPI"])
    experience: list[str] = Field(..., example=["Développeur chez Example Corp"])

class AnonymizeRequest(BaseModel):
    filename: str
    entities: ExtractedEntities
    raw_text: str

# Load spaCy model
try:
    nlp = spacy.load("fr_core_news_lg")
except OSError:
    print("Downloading spaCy model 'fr_core_news_lg'...")
    from spacy.cli import download
    download("fr_core_news_lg")
    nlp = spacy.load("fr_core_news_lg")


app = FastAPI(title="CV Anonymizer API")

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("Warning: Supabase credentials not found. Supabase integration will be disabled.")
    supabase: Client | None = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

@app.get("/")
def read_root():
    """Root endpoint to check if the API is running."""
    return {"message": "Welcome to the CV Anonymizer API!"}

@app.get("/status")
def get_status():
    """Returns the current status of the server, focusing on the app's resource usage."""
    process = psutil.Process(os.getpid())

    # Get process-specific memory usage
    memory_info = process.memory_info()
    memory_used_mb = memory_info.rss / (1024 ** 2)  # rss is typically the most relevant metric

    # Get overall system disk usage (disk usage is not process-specific)
    disk_info = psutil.disk_usage('/')

    return {
        "app_cpu_usage_percent": process.cpu_percent(interval=0.1),
        "app_memory_usage": {
            "used_mb": f"{memory_used_mb:.2f} MB"
        },
        "system_disk_usage": {
            "total": f"{disk_info.total / (1024**3):.2f} GB",
            "used": f"{disk_info.used / (1024**3):.2f} GB",
            "free": f"{disk_info.free / (1024**3):.2f} GB",
            "percent": disk_info.percent
        }
    }

@app.post("/upload")
async def upload_cv(file: UploadFile = File(...)):
    """
    Uploads a CV, extracts text using OCR, and returns the raw text.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    try:
        pdf_bytes = await file.read()

        # --- PDF to Text using pdf2image and Pytesseract ---
        try:
            images = convert_from_bytes(pdf_bytes)
            text = ""
            for img in images:
                # Use pytesseract to extract text, specifying French language
                page_text = pytesseract.image_to_string(img, lang='fra')
                text += page_text + "\n"
        except Exception as ocr_error:
            raise HTTPException(status_code=500, detail=f"OCR processing failed: {ocr_error}. Make sure Tesseract and Poppler are installed and accessible in your system's PATH.")

        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract any text from the PDF.")

        # --- Initial Data Extraction (spaCy + Regex) ---
        doc = nlp(text)
        persons = list(set([ent.text for ent in doc.ents if ent.label_ == "PER"]))
        locations = list(set([ent.text for ent in doc.ents if ent.label_ == "LOC"]))
        emails = list(set(re.findall(r'[\w\.-]+@[\w\.-]+', text)))
        phones = list(set(re.findall(r'(\d{2}[-\.\s]?){4}\d{2}', text)))

        initial_extraction = {
            "persons": persons,
            "locations": locations,
            "emails": emails,
            "phones": phones,
            "skills": [],
            "experience": []
        }

        # --- LLM Refinement ---
        # The LLM will correct the initial extraction and fill in the missing pieces.
        refined_entities = refine_extraction_with_llm(text, initial_extraction)

        # This is the final, clean data object we will save
        final_data_to_save = {
            "filename": file.filename,
            "entities": refined_entities,
            "raw_text": text,
        }

        # --- Supabase Integration ---
        if supabase:
            # Sanitize the filename to be URL-safe for Supabase Storage
            safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', file.filename)
            file_path = f"uploads/{uuid.uuid4()}_{safe_filename}"

            try:
                # 1. Upload original CV to Supabase Storage
                response = supabase.storage.from_("cvs").upload(file_path, pdf_bytes, {"content-type": "application/pdf"})

                # 2. Save extracted data to Supabase Database
                db_response = supabase.table("extractions").insert({
                    "filename": file.filename,
                    "storage_path": file_path,
                    "data": final_data_to_save
                }).execute()

                # Get the ID of the newly inserted row
                new_extraction_id = db_response.data[0]['id']

                return {"extraction_id": new_extraction_id}

            except Exception as e:
                # Log the error but don't block the response to the user
                print(f"Warning: Supabase operation failed: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to save extraction data: {e}")

        # Fallback for when Supabase is not configured
        return extracted_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during file processing: {e}")


def anonymize_text(text: str, entities: ExtractedEntities) -> str:
    """Replaces personal information in the text with anonymized placeholders."""

    # Anonymize persons to initials
    for person in entities.persons:
        initials = "".join([name[0].upper() for name in person.split()])
        text = text.replace(person, f"Person ({initials})")

    # Anonymize emails
    for email in entities.emails:
        text = text.replace(email, "[EMAIL REDACTED]")

    # Anonymize phones
    for phone in entities.phones:
        text = text.replace(phone, "[PHONE REDACTED]")

    # Anonymize locations
    for location in entities.locations:
        text = text.replace(location, "[LOCATION REDACTED]")

    return text


@app.get("/anonymize/{extraction_id}")
async def anonymize_cv_by_id(extraction_id: int):
    """
    Fetches an extraction by its ID, anonymizes the data,
    generates a DOCX file, and returns a download link.
    """
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase is not configured. Cannot fetch extraction data.")

    try:
        # 1. Fetch the extraction data from the database
        response = supabase.table("extractions").select("*").eq("id", extraction_id).single().execute()
        extraction_data = response.data

        if not extraction_data:
            raise HTTPException(status_code=404, detail="Extraction not found.")

        # Reconstruct the request data from the fetched record
        # We need to manually create the Pydantic models for validation and structure
        request_entities = ExtractedEntities(**extraction_data['data']['entities'])
        request = AnonymizeRequest(
            filename=extraction_data['data']['filename'],
            entities=request_entities,
            raw_text=extraction_data['data']['raw_text']
        )

        # 2. Anonymize the text
        anonymized_text = anonymize_text(request.raw_text, request.entities)

        # 3. Generate DOCX
        doc = docx.Document()
        doc.add_heading('CV Anonymisé', 0)
        doc.add_paragraph(anonymized_text)

        doc_io = io.BytesIO()
        doc.save(doc_io)
        doc_io.seek(0)

        # 4. Upload anonymized DOCX to Supabase and get download link
        anonymized_filename = f"anonymized_{request.filename.replace('.pdf', '.docx')}"
        file_path = f"anonymized_cvs/{uuid.uuid4()}_{anonymized_filename}"

        supabase.storage.from_("cvs").upload(file_path, doc_io.getvalue(), {"content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"})

        download_url_response = supabase.storage.from_("cvs").create_signed_url(file_path, 60 * 60 * 24) # 24-hour expiry

        return {"download_url": download_url_response['signedURL']}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
