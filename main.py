import os
import re
import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from pydantic import BaseModel, Field
import fitz  # PyMuPDF
import easyocr
import spacy
from supabase import create_client, Client
import io
from dotenv import load_dotenv
import numpy as np
from PIL import Image
import docx
from docx.shared import Inches

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

# Initialize EasyOCR reader
# This is done once when the application starts
reader = easyocr.Reader(['fr'])

# Load spaCy model
try:
    nlp = spacy.load("fr_core_news_sm")
except OSError:
    print("Downloading spaCy model 'fr_core_news_sm'...")
    from spacy.cli import download
    download("fr_core_news_sm")
    nlp = spacy.load("fr_core_news_sm")


app = FastAPI(title="CV Anonymizer API")

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Warning: Supabase credentials not found. Supabase integration will be disabled.")
    supabase: Client | None = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.get("/")
def read_root():
    """Root endpoint to check if the API is running."""
    return {"message": "Welcome to the CV Anonymizer API!"}

@app.post("/upload")
async def upload_cv(file: UploadFile = File(...)):
    """
    Uploads a CV, extracts text using OCR, and returns the raw text.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    try:
        pdf_bytes = await file.read()

        # --- PDF to Text using PyMuPDF and EasyOCR ---
        text = ""
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page in doc:
                pix = page.get_pixmap()
                img_bytes = pix.tobytes("png")

                # Convert bytes to a numpy array for EasyOCR
                image = Image.open(io.BytesIO(img_bytes))

                # Use EasyOCR to extract text
                result = reader.readtext(np.array(image))
                page_text = " ".join([item[1] for item in result])
                text += page_text + "\n"

        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract any text from the PDF.")

        # --- Entity Extraction using spaCy and Regex ---
        doc = nlp(text)

        # Extract entities
        persons = [ent.text for ent in doc.ents if ent.label_ == "PER"]
        locations = [ent.text for ent in doc.ents if ent.label_ == "LOC"]

        # Regex for emails and phone numbers
        emails = re.findall(r'[\w\.-]+@[\w\.-]+', text)
        phones = re.findall(r'(\d{2}[-\.\s]?){4}\d{2}', text)

        # For now, skills and experience are placeholders
        # This can be improved with custom NER models or LLMs
        skills = []
        experience = []

        extracted_data = {
            "filename": file.filename,
            "entities": {
                "persons": list(set(persons)),
                "locations": list(set(locations)),
                "emails": list(set(emails)),
                "phones": list(set(phones)),
                "skills": skills,
                "experience": experience,
            },
            "raw_text": text,
        }

        # --- Supabase Integration ---
        if supabase:
            # 1. Upload original CV to Supabase Storage
            file_path = f"uploads/{uuid.uuid4()}_{file.filename}"
            try:
                response = supabase.storage.from_("cvs").upload(file_path, pdf_bytes, {"content-type": "application/pdf"})

                # 2. Save extracted data to Supabase Database
                db_response = supabase.table("extractions").insert({
                    "filename": file.filename,
                    "storage_path": file_path,
                    "data": extracted_data["entities"]
                }).execute()

            except Exception as e:
                # Log the error but don't block the response to the user
                print(f"Warning: Supabase operation failed: {e}")


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


@app.post("/anonymize")
async def anonymize_cv(request: AnonymizeRequest):
    """
    Takes extracted data, anonymizes it, generates a DOCX file,
    and returns a download link.
    """

    anonymized_text = anonymize_text(request.raw_text, request.entities)

    # --- Generate DOCX ---
    doc = docx.Document()
    doc.add_heading('CV Anonymisé', 0)
    doc.add_paragraph(anonymized_text)

    # Save doc to a temporary in-memory file
    doc_io = io.BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)

    # --- Supabase Integration ---
    if supabase:
        anonymized_filename = f"anonymized_{request.filename.replace('.pdf', '.docx')}"
        file_path = f"anonymized_cvs/{uuid.uuid4()}_{anonymized_filename}"

        try:
            supabase.storage.from_("cvs").upload(file_path, doc_io.getvalue(), {"content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"})

            # Generate a signed URL for download
            download_url = supabase.storage.from_("cvs").create_signed_url(file_path, 60 * 60 * 24) # 24-hour expiry

            return {"download_url": download_url['signedURL']}

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload to Supabase: {e}")
    else:
        return {"message": "Anonymized document generated, but Supabase is not configured for upload.", "anonymized_text": anonymized_text}
