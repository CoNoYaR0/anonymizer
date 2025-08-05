import io
import logging
import base64
from typing import IO
from openai import OpenAI
from pdf2image import convert_from_bytes
from PIL import Image
from jinja2 import Environment, TemplateSyntaxError

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


def _validate_jinja2_syntax(template_string: str):
    """
    Validates the Jinja2 syntax of a template string.
    Raises jinja2.TemplateSyntaxError on failure.
    """
    logger.info("Validating Jinja2 syntax.")
    try:
        env = Environment()
        env.parse(template_string)
        logger.info("Jinja2 syntax is valid.")
    except TemplateSyntaxError as e:
        logger.warning(f"Jinja2 syntax validation failed: {e}")
        raise e


def create_template_from_pdf(file_stream: IO[bytes]) -> str:
    """
    Orchestrates the creation of a Jinja2 HTML template from a PDF file.
    This is a two-step process:
    1. Convert the PDF's visual layout to raw HTML.
    2. Use a second LLM call to inject Jinja2 placeholders into the HTML,
       with a validation and self-correction loop.
    """
    logger.info("[template_builder.create_template_from_pdf] Orchestrating template creation.")

    # Step 1: Convert PDF to raw HTML
    raw_html = _pdf_to_html(file_stream)

    # Step 2: Inject Jinja2 placeholders with a validation and self-correction loop
    max_retries = 3
    last_error = None
    templated_html = ""
    client = OpenAI()

    system_prompt = """
You are a Jinja2 templating expert. Your task is to take a raw HTML file representing a CV and intelligently replace the specific personal details (names, companies, dates, skills, etc.) with the correct Jinja2 placeholders.

**Rules:**
1.  **PERFECT SYNTAX:** Your generated Jinja2 code MUST be syntactically flawless. Every `{% for ... %}` must have a matching `{% endfor %}`.
2.  **NO HTML CHANGES:** Do NOT change the HTML structure or CSS styling in any way.
3.  **STANDARD PLACEHOLDERS:**
    -   Names: `{{ name }}`
    -   Job Titles: `{{ title }}`
    -   Contact Info: `{{ email }}`, `{{ phone }}`, `{{ location }}`
4.  **LOOPS:**
    -   Work Experience/Education: Use `{% for job in experiences %}` or `{% for edu in educations %}`.
    -   Inside loops, use correct variables: `{{ job.title }}`, `{{ edu.institution }}`.
    -   Skills (grouped by category): Use `{% for category, tools in skills.items() %}`.
5.  **OUTPUT:** Your output MUST be only the final, templated HTML code. Do not add commentary.
"""
    user_html_prompt = f"Here is the raw HTML to be templated:\n\n```html\n{raw_html}\n```"


    for attempt in range(max_retries):
        logger.info(f"Attempt {attempt + 1} of {max_retries} to inject and validate Jinja2 syntax.")

        feedback_prompt = ""
        if last_error:
            feedback_prompt = (
                "\n\n---\n"
                "**IMPORTANT:** Your previous attempt failed with a Jinja2 syntax error. "
                "You MUST fix this specific issue. Do not repeat the mistake.\n"
                f"**Error Message:** `{last_error}`\n"
                "---"
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_html_prompt + feedback_prompt},
        ]

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.0,
            )
            templated_html = response.choices[0].message.content
            # Clean up markdown fences
            if templated_html.startswith("```html"):
                templated_html = templated_html[7:]
            if templated_html.endswith("```"):
                templated_html = templated_html[:-3]

            # Validate the generated syntax
            _validate_jinja2_syntax(templated_html)

            logger.info("Successfully generated and validated template.")
            return templated_html.strip()

        except TemplateSyntaxError as e:
            logger.warning(f"Attempt {attempt + 1} failed validation. Error: {e}")
            last_error = e
        except Exception as e:
            logger.error(f"An unexpected error occurred during Jinja2 injection attempt {attempt + 1}: {e}", exc_info=True)
            raise ValueError(f"An unexpected error occurred during template generation: {e}")

    logger.error("Failed to generate a valid template after multiple retries.")
    raise ValueError(f"Failed to create a valid template after {max_retries} attempts. Last syntax error: {last_error}")
