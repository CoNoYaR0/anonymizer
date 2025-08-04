import io
from docxtpl import DocxTemplate

TEMPLATE_PATH = "templates/cv_template.docx"

def generate_cv_from_template(data: dict) -> io.BytesIO:
    """
    Renders the final CV document using the Jinja2 template.

    Args:
        data: A dictionary containing the extracted and refined CV data.

    Returns:
        A BytesIO stream of the generated .docx file.
    """
    try:
        doc = DocxTemplate(TEMPLATE_PATH)
    except Exception as e:
        # This will happen if the create_template.py script hasn't been run successfully.
        raise FileNotFoundError(f"Template not found at '{TEMPLATE_PATH}'. Please run the `create_template.py` script first.") from e

    # Prepare the context for Jinja2 rendering
    entities = data.get('data', {}).get('entities', {})
    context = {}

    # --- Personal Info ---
    persons = entities.get('persons', [])
    if persons:
        full_name = persons[0]
        context['initials'] = "".join([name[0].upper() for name in full_name.split()])
        context['title'] = entities.get('titles', ["N/A"])[0]
    else:
        context['initials'] = "N/A"
        context['title'] = "N/A"

    # --- Experience ---
    experiences = entities.get('experience', [])
    context['experiences'] = experiences

    total_experience_years = 0
    if experiences:
        # Assuming experiences are sorted chronologically
        context['current_company'] = experiences[0].get('company', 'N/A')
        for exp in experiences:
            # Simple parsing of 'period' (e.g., "2 years 5 months")
            try:
                years = int(exp.get('period', '0').split(' ')[0])
                total_experience_years += years
            except (ValueError, IndexError):
                pass # Ignore if period is not in the expected format
    else:
        context['current_company'] = "N/A"

    context['experience_years'] = total_experience_years

    # --- Certifications & Formations ---
    context['certifications'] = entities.get('certifications', [])

    # --- Skills ---
    context['skills'] = entities.get('skills', {})

    # --- Languages ---
    context['languages'] = entities.get('languages', [])

    # Render the document
    try:
        doc.render(context)
    except Exception as e:
        import os
        import logging
        logger = logging.getLogger(__name__)
        DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
        logger.error(f"Jinja2 Template Syntax Error: {e}")

        if DEBUG:
            try:
                # In debug mode, save the raw XML of the template for inspection
                xml_content = doc.get_xml()
                debug_path = "templates/debug_template.xml"
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(xml_content)
                logger.info(f"Saved raw template XML for debugging to: {debug_path}")
                logger.info("Inspect this file to find the exact location of the syntax error in your .docx template.")
            except Exception as debug_exc:
                logger.error(f"Failed to save debug XML file: {debug_exc}")
        raise e


    # Save the document to a byte stream
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)

    return file_stream
