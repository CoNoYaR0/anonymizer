import io
import logging
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader

# Configure logger
logger = logging.getLogger(__name__)

def render_html_to_pdf(template_path: str, json_data: dict) -> io.BytesIO:
    """
    Renders a Jinja2 HTML template with the given JSON data and converts it to a PDF.

    Args:
        template_path: The path to the HTML template file.
        json_data: A dictionary containing the data to render.

    Returns:
        A BytesIO stream of the generated PDF file.
    """
    logger.info(f"Rendering template '{template_path}' to PDF.")

    try:
        # Set up Jinja2 environment
        env = Environment(loader=FileSystemLoader('templates/html'))
        template = env.get_template(template_path)

        # Render the HTML with the provided data
        rendered_html = template.render(json_data)
        logger.debug("HTML template rendered successfully.")

        # Convert the rendered HTML to PDF
        pdf_stream = io.BytesIO()
        HTML(string=rendered_html).write_pdf(pdf_stream)
        pdf_stream.seek(0)

        logger.info("Successfully rendered HTML to PDF.")
        return pdf_stream

    except Exception as e:
        logger.error(f"Failed to render HTML to PDF: {e}", exc_info=True)
        raise ValueError("An error occurred during the PDF rendering process.")
