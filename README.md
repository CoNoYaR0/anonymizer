# CV Anonymizer

This project is a Python script that automates the process of anonymizing CVs. It takes a CV in PDF format as input, extracts the relevant information, anonymizes the personal data, and generates a new CV in DOCX format.

## How it works

The script uses a combination of Optical Character Recognition (OCR), Natural Language Processing (NLP), and regular expressions to extract and anonymize the information from the CV.

Here's a step-by-step breakdown of the process:

1.  **PDF to Text:** The script first converts the input PDF file into plain text using Tesseract OCR. This is done by first converting each page of the PDF into an image and then running OCR on each image.
2.  **Information Extraction:** The script then uses a combination of NLP and regular expressions to extract the following information from the text:
    *   **Name:** The script uses spaCy's Named Entity Recognition (NER) to identify the candidate's name.
    *   **Email and Phone Number:** The script uses regular expressions to find the email address and phone number.
    *   **Sections:** The script uses a keyword-based approach to identify the main sections of the CV, such as "Experiences," "Competencies," "Education," and "Technologies."
3.  **Anonymization:** Once the personal information has been extracted, the script anonymizes it as follows:
    *   **Name:** The candidate's name is replaced with their initials (e.g., "John Doe" becomes "JD").
    *   **Email and Phone Number:** The email and phone number are replaced with placeholders (e.g., "email_001@example.com" and "phone_001").
4.  **Output Generation:** Finally, the script generates two output files:
    *   **JSON file:** A JSON file containing the extracted and anonymized data.
    *   **DOCX file:** A new CV in DOCX format, created from a template and populated with the anonymized data.

## How to use

To use the script, you need to have Python 3.10 or higher installed, as well as the following dependencies:

*   `spacy`
*   `python-docx`
*   `pytesseract`
*   `pdf2image`
*   `Pillow`
*   `tesseract`
*   `poppler`

You can install the Python dependencies using pip:

```
pip install spacy python-docx pytesseract pdf2image Pillow
```

You will also need to download the French spaCy model:

```
python -m spacy download fr_core_news_md
```

Finally, you will need to install Tesseract and Poppler. The installation process for these dependencies will vary depending on your operating system.

**On Debian-based Linux distributions (such as Ubuntu), you can install them using the following commands:**

```
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-fra poppler-utils
```

Once you have installed all the dependencies, you can run the script from the command line:

```
python anonymizer.py
```

The script will process the CV located at `uploads/CV Jebrane TABANA 2025 (Ingénieur Senior QA-Test Lead).pdf` and generate the anonymized output files in the `outputs` directory.

## Project Structure

```
.
├── anonymizer.py
├── outputs
│   ├── anonymized_cv_P.docx
│   └── anonymized_cv_P.json
├── Project Overview.md
├── README.md
├── templates
│   ├── Dossier_de_competences_KOUKA_JTA.doc
│   └── template_cv.docx
└── uploads
    └── CV Jebrane TABANA 2025 (Ingénieur Senior QA-Test Lead).pdf
```

*   `anonymizer.py`: The main Python script.
*   `outputs`: This directory contains the anonymized output files.
*   `Project Overview.md`: A Markdown file containing a high-level overview of the project.
*   `README.md`: This file.
*   `templates`: This directory contains the template files for the output CV.
*   `uploads`: This directory contains the input CVs.

## Limitations

The current implementation has a few limitations:

*   **Section Extraction:** The section extraction is based on a simple keyword-matching approach and may not be accurate for all CVs.
*   **Language:** The script is currently configured to work with French CVs. To use it with other languages, you will need to download the appropriate spaCy model and Tesseract language pack.
*   **File Formats:** The script currently only supports PDF files as input.
```
