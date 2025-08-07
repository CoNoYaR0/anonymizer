import os
from typing import Dict, Any
from dotenv import load_dotenv

# Note: The actual imports for pdf2image, pytesseract, and docx will be needed
# when implementing the TODOs. For the skeleton, we will just define the functions.
# from pdf2image import convert_from_path
# import pytesseract
# from docx import Document

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def _extract_text_from_pdf(file_path: str) -> str:
    """
    Extracts text from a PDF file using OCR.
    Converts PDF pages to images and then uses Tesseract to extract text.

    Args:
        file_path: The path to the PDF file.

    Returns:
        The extracted raw text as a single string.
    """
    # TODO: Implement the PDF OCR logic.
    # 1. Use `pdf2image.convert_from_path` to get a list of PIL images.
    # 2. Iterate through the images and use `pytesseract.image_to_string`
    #    to extract text from each image. The `AGENTS.md` specifies using
    #    the French language model (`lang='fra'`).
    # 3. Concatenate the text from all pages.
    print(f"TODO: Extracting text from PDF: {file_path} using OCR (lang='fra').")
    return "Placeholder text from a PDF document."

def _extract_text_from_image(file_path: str) -> str:
    """
    Extracts text from an image file using OCR.

    Args:
        file_path: The path to the image file (e.g., PNG, JPG).

    Returns:
        The extracted raw text.
    """
    # TODO: Implement the image OCR logic.
    # Use `pytesseract.image_to_string` on the image file, specifying `lang='fra'`.
    print(f"TODO: Extracting text from Image: {file_path} using OCR (lang='fra').")
    return "Placeholder text from an image file."

def _extract_text_from_docx(file_path: str) -> str:
    """
    Extracts text from a DOCX file.

    Args:
        file_path: The path to the DOCX file.

    Returns:
        The extracted raw text.
    """
    # TODO: Implement the DOCX text extraction logic.
    # Use the `python-docx` library to open the file and iterate through
    # paragraphs to extract all the text.
    print(f"TODO: Extracting text from DOCX: {file_path}.")
    return "Placeholder text from a DOCX file."

def _get_structured_data_from_text(raw_text: str) -> Dict[str, Any]:
    """
    Uses an LLM to parse raw text and return a structured JSON object.

    Args:
        raw_text: A string containing all the text extracted from a CV.

    Returns:
        A dictionary representing the structured data of the CV (e.g.,
        {'name': 'John Doe', 'experience': [...]}).

    Raises:
        Exception: If the OpenAI API key is missing.
    """
    if not OPENAI_API_KEY:
        raise Exception("OPENAI_API_KEY is not set.")

    # TODO: Implement the LLM call to structure the data.
    # 1. Define a clear, canonical JSON schema that you want the LLM to return.
    # 2. Create a prompt that includes the raw text and instructions for the LLM
    #    to extract the information and format it according to your schema.
    # 3. Call the OpenAI API (GPT-4o) with the prompt.
    # 4. Parse the JSON response from the LLM.
    print("TODO: Calling OpenAI API to structure the extracted text into JSON.")

    # Placeholder return value
    return {
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "phone": "123-456-7890",
        "summary": "A placeholder summary of skills and experience.",
        "experience": [
            {
                "title": "Software Engineer",
                "company": "Tech Corp",
                "dates": "Jan 2022 - Present",
                "description": "Developing cool stuff."
            }
        ],
        "education": [
            {
                "degree": "B.S. in Computer Science",
                "university": "State University",
                "year": 2021
            }
        ]
    }

def extract_content_from_cv(file_path: str, mime_type: str) -> Dict[str, Any]:
    """
    Orchestrates the content extraction process based on the file's MIME type.

    Args:
        file_path: The path to the uploaded CV file.
        mime_type: The MIME type of the file (e.g., 'application/pdf', 'image/png').

    Returns:
        A dictionary containing the structured CV data.

    Raises:
        ValueError: If the file type is unsupported.
    """
    raw_text = ""
    if mime_type == 'application/pdf':
        raw_text = _extract_text_from_pdf(file_path)
    elif mime_type.startswith('image/'):
        raw_text = _extract_text_from_image(file_path)
    elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        raw_text = _extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {mime_type}")

    structured_data = _get_structured_data_from_text(raw_text)

    return structured_data
