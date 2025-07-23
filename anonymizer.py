import os
import json
import re
import spacy
from PIL import Image
import pytesseract
from docx import Document
from pdf2image import convert_from_path

# Load the French spaCy model
nlp = spacy.load("fr_core_news_md")

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF file using Tesseract OCR.
    """
    try:
        images = convert_from_path(pdf_path)
        text = ""
        for image in images:
            text += pytesseract.image_to_string(image, lang='fra')
        return text
    except Exception as e:
        return f"Error extracting text from PDF: {e}"

def extract_contact_info(text):
    """
    Extracts contact information (email and phone number) from the text.
    """
    email = re.search(r'[\w\.-]+@[\w\.-]+', text)
    phone = re.search(r'(\d{2}[-\.\s]?){4}\d{2}', text)
    return email.group(0) if email else None, phone.group(0) if phone else None

def extract_name(text):
    """
    Extracts the name from the text using spaCy's NER.
    """
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "PER":
            return ent.text
    return None

def pseudonymize_name(name):
    """
    Pseudonymizes the name by taking the initials.
    """
    if not name:
        return None
    return "".join([n[0] for n in name.split()]).upper()

def extract_sections(text):
    """
    Extracts sections (experiences, competencies, education, technologies) from the text.
    This is a simplified implementation and may need to be improved.
    """
    sections = {
        "experiences": [],
        "competencies": [],
        "education": [],
        "technologies": []
    }

    # This is a placeholder for the actual implementation
    # A more robust solution would use regex or NLP to identify sections and their content

    lines = text.split('\n')
    current_section = None

    for line in lines:
        if "expérience" in line.lower():
            current_section = "experiences"
        elif "compétence" in line.lower():
            current_section = "competencies"
        elif "formation" in line.lower() or "cursus" in line.lower():
            current_section = "education"
        elif "technologies" in line.lower():
            current_section = "technologies"
        elif current_section and line.strip():
            sections[current_section].append(line.strip())

    return sections

def create_docx(template_path, output_path, data):
    """
    Creates a DOCX file from a template and fills it with the provided data.
    """
    try:
        doc = Document(template_path)
        for p in doc.paragraphs:
            for key, value in data.items():
                if f"{{{{{key}}}}}" in p.text:
                    inline = p.runs
                    # Replace strings and retain formatting
                    for i in range(len(inline)):
                        if f"{{{{{key}}}}}" in inline[i].text:
                            text = inline[i].text.replace(f"{{{{{key}}}}}", str(value))
                            inline[i].text = text
        doc.save(output_path)
        return True
    except Exception as e:
        print(f"Error creating DOCX: {e}")
        return False

def main():
    """
    Main function to run the anonymization process.
    """
    # File paths
    pdf_path = "uploads/CV Jebrane TABANA 2025 (Ingénieur Senior QA-Test Lead).pdf"
    template_path = "templates/template_cv.docx"
    output_dir = "outputs"

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 1. Extract text from PDF
    text = extract_text_from_pdf(pdf_path)
    if text.startswith("Error"):
        print(text)
        return

    # 2. Extract information
    name = extract_name(text)
    email, phone = extract_contact_info(text)
    sections = extract_sections(text)

    # 3. Pseudonymize
    candidate_id = pseudonymize_name(name)

    # 4. Build JSON
    data = {
        "candidate_id": candidate_id,
        "contact": {
            "email": "email_001@example.com",
            "phone": "phone_001"
        },
        "experiences": sections["experiences"],
        "competencies": sections["competencies"],
        "education": sections["education"],
        "technologies": sections["technologies"]
    }

    # Save JSON
    json_output_path = os.path.join(output_dir, f"anonymized_cv_{candidate_id}.json")
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # 5. Create DOCX
    docx_output_path = os.path.join(output_dir, f"anonymized_cv_{candidate_id}.docx")

    # Data for the docx template
    docx_data = {
        "candidate_id": candidate_id,
        "email": "email_001@example.com",
        "phone": "phone_001",
        "experiences": "\n".join(sections["experiences"]),
        "competencies": "\n".join(sections["competencies"]),
        "education": "\n".join(sections["education"]),
        "technologies": "\n".join(sections["technologies"]),
    }

    if not create_docx(template_path, docx_output_path, docx_data):
        print("Failed to create DOCX file.")

    # Report missing fields
    errors = []
    if not name:
        errors.append("Name not found.")
    if not email:
        errors.append("Email not found.")
    if not phone:
        errors.append("Phone number not found.")

    if errors:
        with open(os.path.join(output_dir, "errors.txt"), "w") as f:
            for error in errors:
                f.write(f"{error}\n")

if __name__ == "__main__":
    main()
