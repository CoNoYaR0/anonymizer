import io
import logging
import os
from weasyprint import HTML
from liquid import Liquid

# Configure logger
logger = logging.getLogger(__name__)

def render_html_to_pdf(template_name: str, json_data: dict) -> io.BytesIO:
    """
    Renders a Liquid HTML template with the given JSON data and converts it to a PDF.

    Args:
        template_name: The filename of the HTML template in the 'templates/html' directory.
        json_data: A dictionary containing the data to render.

    Returns:
        A BytesIO stream of the generated PDF file.
    """
    logger.info(f"Rendering template '{template_name}' with Liquid engine to PDF.")

    template_path = os.path.join('templates/html', template_name)

    try:
        # Read the template content from the file
        with open(template_path, 'r', encoding='utf-8') as f:
            template_string = f.read()

        # Create a Liquid template object from the string content
        template = Liquid(template_string, from_file=False)

        # Render the HTML with the provided data
        rendered_html = template.render(json_data)
        logger.debug("HTML template rendered successfully with Liquid.")

        # Convert the rendered HTML to PDF using WeasyPrint
        pdf_stream = io.BytesIO()
        HTML(string=rendered_html).write_pdf(pdf_stream)
        pdf_stream.seek(0)

        logger.info("Successfully rendered HTML to PDF.")
        return pdf_stream

    except FileNotFoundError:
        logger.error(f"Template file not found at '{template_path}'")
        raise ValueError(f"Template '{template_name}' not found.")
    except Exception as e:
        logger.error(f"Failed to render HTML to PDF: {e}", exc_info=True)
        raise ValueError("An error occurred during the PDF rendering process.")
