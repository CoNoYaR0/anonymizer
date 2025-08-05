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
    logger.info("[template_builder._pdf_to_html] Starting PDF to HTML conversion.")
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
    This is a two-step process:
    1. Convert the PDF's visual layout to raw HTML.
    2. Use a second LLM call to inject Jinja2 placeholders into the HTML.
    """
    logger.info("[template_builder.create_template_from_pdf] Orchestrating template creation.")

    # Step 1: Convert PDF to raw HTML
    raw_html = _pdf_to_html(file_stream)

    # Step 2: Inject Jinja2 placeholders using a second LLM call
    logger.info("Sending raw HTML to LLM for Jinja2 placeholder injection.")
    client = OpenAI()
    system_prompt = """
You are a Jinja2 templating expert. Your task is to take a raw HTML file representing a CV and intelligently replace the specific personal details (names, companies, dates, skills, etc.) with the correct Jinja2 placeholders.

**Rules:**
1.  **DO NOT** change the HTML structure or CSS styling in any way.
2.  Replace names with `{{ name }}`.
3.  Replace job titles with `{{ title }}`.
4.  Replace contact info (email, phone, location) with `{{ email }}`, `{{ phone }}`, `{{ location }}`.
5.  For repeating sections like work experience or education, you MUST use `{% for ... %}` loops. For example: `{% for job in experiences %}` or `{% for edu in educations %}`.
6.  Inside loops, use the correct variable names, e.g., `{{ job.title }}`, `{{ job.company }}`, `{{ edu.title }}`.
7.  For lists of skills, which are often grouped by category, use a dictionary loop: `{% for category, tools in skills.items() %}`.
8.  Your output MUST be only the final, templated HTML code. Do not add commentary.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o", # Use a powerful model for this complex task
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here is the raw HTML to be templated:\n\n```html\n{raw_html}\n```"},
            ],
            temperature=0.0,
        )
        templated_html = response.choices[0].message.content
        # Clean up markdown fences
        if templated_html.startswith("```html"):
            templated_html = templated_html[7:]
        if templated_html.endswith("```"):
            templated_html = templated_html[:-3]

        logger.info("Successfully injected Jinja2 placeholders into HTML.")
        return templated_html.strip()
    except Exception as e:
        logger.error(f"LLM Jinja2 injection failed: {e}", exc_info=True)
        raise ValueError("Failed to inject Jinja2 placeholders into the HTML.")
