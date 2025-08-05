import io
import logging
import base64
from typing import IO
from openai import OpenAI
from pdf2image import convert_from_bytes
from PIL import Image

# Configure logger
logger = logging.getLogger(__name__)

def _pdf_to_html(file_stream: IO[bytes]) -> str:
    """
    Converts a PDF file stream to a single HTML string with inline CSS
    by first converting each page to an image and then sending them to a
    multimodal LLM.
    """
    logger.info("Converting PDF to images for vision analysis.")
    try:
        pdf_bytes = file_stream.read()
        images = convert_from_bytes(pdf_bytes)
    except Exception as e:
        logger.error(f"Failed to convert PDF to images: {e}", exc_info=True)
        raise ValueError("Could not process the PDF file. It might be corrupted or in an unsupported format.")

    if not images:
        raise ValueError("PDF file did not contain any pages or could not be read.")

    logger.info(f"Successfully converted PDF into {len(images)} image(s).")

    client = OpenAI()

    # Prepare the list of images for the API call
    image_messages = []
    for i, image in enumerate(images):
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        image_messages.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{img_base64}"
            }
        })
        logger.debug(f"Prepared page {i+1} for LLM vision.")

    system_prompt = """
You are an expert web developer. Your task is to look at a sequence of images from a CV and perfectly replicate its combined layout and content as a single, clean HTML file with inline CSS.

**Rules:**
1.  You MUST use inline CSS for styling (e.g., `<p style="color: blue;">`).
2.  Combine the content from all images into a single, coherent HTML document.
3.  The output MUST be a single, complete HTML string.
4.  Do not include any commentary or explanation outside of the HTML code.
5.  Replicate the text content and layout as precisely as possible.
"""
    user_content = [
        {
            "type": "text",
            "text": "Please convert this sequence of CV pages into a single HTML file with inline CSS."
        }
    ]
    user_content.extend(image_messages)

    logger.info("Sending PDF images to vision-capable LLM for HTML conversion.")
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.0,
        )
        html_content = response.choices[0].message.content
        # Clean up markdown fences if the LLM adds them
        if html_content.startswith("```html"):
            html_content = html_content[7:]
        if html_content.endswith("```"):
            html_content = html_content[:-3]

        logger.info("Successfully received HTML from LLM.")
        return html_content.strip()

    except Exception as e:
        logger.error(f"LLM PDF-to-HTML conversion failed: {e}", exc_info=True)
        raise ValueError("Failed to convert PDF to HTML using the LLM.")


def create_template_from_pdf(file_stream: IO[bytes]) -> str:
    """
    Orchestrates the creation of a Jinja2 HTML template from a PDF file.

    Note: This is a simplified placeholder. A real implementation would require
    a much more sophisticated second LLM call or complex regex to identify and
    replace specific text with Jinja2 placeholders while preserving the surrounding HTML.
    For this version, we will just return the raw HTML as a proof of concept.
    """
    html_content = _pdf_to_html(file_stream)

    # TODO: Implement sophisticated text-to-Jinja2 replacement logic here.
    # For example, find "John Doe" in the HTML and replace it with "{{ name }}".
    # This is a non-trivial task that requires careful parsing to avoid breaking HTML tags.
    logger.warning("Template creation is in proof-of-concept stage. Placeholder injection is not yet implemented.")

    templated_html = html_content # Placeholder for now

    return templated_html
