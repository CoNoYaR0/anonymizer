import io
import zipfile
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
        # --- In-memory template patching using zipfile ---
        # The template has a syntax error. This logic corrects it in memory by
        # rebuilding the .docx file without the erroneous paragraph.

        bad_paragraph = (
            '<w:p w14:paraId="1FAF1A35" w14:textId="77777777" w:rsidR="0094773F" '
            'w:rsidRDefault="0094773F" w:rsidP="0094773F"><w:pPr><w:ind w:left="360"/>'
            '<w:rPr><w:lang w:val="fr-FR" w:eastAsia="en-GB"/></w:rPr></w:pPr><w:r>'
            '<w:t>{% endfor %}</w:t></w:r></w:p>'
        )

        fixed_template_stream = io.BytesIO()
        with zipfile.ZipFile(TEMPLATE_PATH, 'r') as original_zip:
            with zipfile.ZipFile(fixed_template_stream, 'w', zipfile.ZIP_DEFLATED) as fixed_zip:
                for item in original_zip.infolist():
                    if item.filename == 'word/document.xml':
                        xml_content = original_zip.read(item.filename).decode('utf-8')
                        # Only patch if the bad paragraph exists
                        if bad_paragraph in xml_content:
                            fixed_xml_content = xml_content.replace(bad_paragraph, '')
                            fixed_zip.writestr(item.filename, fixed_xml_content.encode('utf-8'))
                        else:
                            fixed_zip.writestr(item.filename, original_zip.read(item.filename))
                    else:
                        fixed_zip.writestr(item.filename, original_zip.read(item.filename))

        fixed_template_stream.seek(0)
        doc = DocxTemplate(fixed_template_stream)

    except Exception as e:
        # If patching fails, fall back to the original template
        # to get the original error, which is better than a new one.
        import logging
        logging.warning(f"Template patching failed: {e}. Falling back to original template.")
        doc = DocxTemplate(TEMPLATE_PATH)

    # Prepare the context for Jinja2 rendering
    # The 'data' object from the DB is nested, so we extract the entities
    entities = data.get('data', {}).get('entities', {})

    context = entities.copy()

    # Calculate initials
    persons = context.get('persons', [])
    if persons:
        # Assuming the first person is the main subject
        full_name = persons[0]
        initials = "".join([name[0].upper() for name in full_name.split()])
        context['initiales'] = initials
    else:
        context['initiales'] = "N/A"

    # docxtpl can handle loops, so we pass the lists directly
    context['experiences'] = context.get('experience', [])
    context['skills'] = context.get('skills', [])


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
