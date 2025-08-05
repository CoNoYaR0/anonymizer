import io
import logging
import base64
from typing import IO
from openai import OpenAI
from pdf2image import convert_from_bytes
from PIL import Image
from liquid import Liquid

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
You are a senior digital archivist and elite HTML/CSS engineer.

Your mission is to **reconstruct, with extreme visual precision**, a CV from one or more input images (scanned from PDF), by producing a **pixel-perfect, full HTML document** with **inline CSS**.

---

🚨 YOUR OUTPUT MUST REPLICATE THE DESIGN **EXACTLY**.
This is not a markdown conversion, not an interpretation, and not a simplification. You are recreating a UI down to the pixel and color.

---

🔒 STRICT REQUIREMENTS (NO EXCEPTIONS):

1. 🎯 **PIXEL-PERFECT REPLICATION**:
   - Every layout element (spacing, margin, padding, line height, indentation, positioning) must match the image exactly.
   - Maintain **column structure**, **grid alignment**, and **relative spacing** as shown visually.

2. 🎨 **EXACT COLORS, FONTS, AND STYLES**:
   - Colors must match **exactly** (e.g., if a bullet point is `#ff3300`, use that exact hex).
   - Preserve **font families**, **sizes**, **weights**, **line spacing**, and **text alignment**.
   - If a heading is bold and orange in the source, it must be bold and `#ff3300` in HTML.
   - DO NOT substitute approximate styles.

3. ➖ **RESPECT ALL DESIGN ELEMENTS**:
   - Horizontal or vertical lines, separators, shapes, spacers, and icons must be included using `<hr>`, `<div>`, or styled elements.
   - Alignments, indentation, bullet styles, and spacing between blocks must be preserved.

4. 🧱 **INLINE CSS ONLY**:
   - All styling must be done via `style="..."` inline attributes.
   - Do not use `<style>`, `<link>`, or external files.

5. 📦 **MERGE ALL IMAGES INTO ONE PAGE**:
   - If there are multiple input images, concatenate them into a **single, flowing HTML page**, in the order shown.

6. ✍️ **PRESERVE TEXT AS-IS**:
   - Do not reword, guess, translate, or reinterpret any part of the text.
   - If a word is unreadable, write `[UNCLEAR]`.

7. 🧼 **OUTPUT ONLY CLEAN, FINAL HTML**:
   - Do not wrap in markdown fences
   - Do not include commentary or meta text
   - No broken or unfinished tags

---

📌 IMPORTANT: Your output will be parsed and processed programmatically.
Even minor style deviations (wrong color, spacing, font weight) will break our workflow.
This is not design inspiration — this is **digital reconstruction with engineering-grade fidelity**.

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
            temperature=0.2,
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


def _validate_liquid_syntax(template_string: str):
    """
    Validates the Liquid syntax of a template string.
    Raises an exception on failure.
    """
    logger.info("Validating Liquid syntax.")
    try:
        Liquid(template_string, from_file=False)
        logger.info("Liquid syntax is valid.")
    except Exception as e:
        # Re-raise, to be caught by the main loop
        raise e


def create_template_from_pdf(file_stream: IO[bytes]) -> str:
    """
    Orchestrates the creation of a Liquid HTML template from a PDF file.
    This is a two-step process:
    1. Convert the PDF's visual layout to raw HTML.
    2. Use a second LLM call to inject Liquid placeholders into the HTML,
       with a validation and self-correction loop.
    """
    logger.info("[template_builder.create_template_from_pdf] Orchestrating template creation.")

    # Step 1: Convert PDF to raw HTML
    raw_html = _pdf_to_html(file_stream)

    # Step 2: Inject Liquid placeholders with a validation and self-correction loop
    max_retries = 3
    last_error = None
    templated_html = ""
    client = OpenAI()

    system_prompt = """
You are an expert in Liquid templating.

Your task is to take a fully rendered, static HTML CV and **intelligently replace static personal content** with dynamic Liquid template tags.

🎯 Your goal is to inject Liquid placeholders in a way that makes the file reusable as a dynamic template, without breaking the structure or formatting.

🔒 RULES:

1. **DO NOT MODIFY HTML STRUCTURE**
   Preserve all HTML tags, inline styles, and layout exactly as they are.

2. **INJECT ONLY VALID LIQUID**
   All Liquid tags must be 100% syntactically valid.
   - Every `{% for ... %}` must be matched with `{% endfor %}`
   - All variable names must follow the given standard

3. **USE THESE STANDARD VARIABLES**:
   - Personal info:
     - `{{ name }}`, `{{ title }}`, `{{ years_experience }}`
     - `{{ email }}`, `{{ phone }}`, `{{ location }}`
   - Work experience:
     - `{% for job in experiences %}`
     - `{{ job.title }}`, `{{ job.company }}`, `{{ job.start_date }}`, `{{ job.end_date }}`, `{{ job.location }}`
     - `{{ job.context }}`, `{{ job.technical_environment }}`
     - Looped sections: `job.missions`, `job.results`, `job.security`, `job.monitoring`, etc.
   - Education:
     - `{% for edu in educations %}`
     - `{{ edu.date }}`, `{{ edu.degree }}`, `{{ edu.institution }}`
   - Skills:
     - `{% for skill in skills %}`
     - `{{ skill[0] }}: {{ skill[1] | join: ', ' }}`

4. **FILL ALL DYNAMIC FIELDS**
   Ensure that every personal/variable field is replaced with a Liquid tag.
   If unsure, leave static content.

5. **NEVER OUTPUT EXPLANATIONS**
   Only output the final, fully templated HTML. No markdown, no comments, no prefix/suffix.

6. **IF RETRYING AFTER ERROR**, use the additional instruction:
   - `IMPORTANT: Your previous attempt failed with a Liquid syntax error. You MUST fix this specific issue: [error_message_here]`

"""
    user_html_prompt = f"Here is the raw HTML to be templated:\n\n```html\n{raw_html}\n```"


    for attempt in range(max_retries):
        logger.info(f"Attempt {attempt + 1} of {max_retries} to inject and validate Liquid syntax.")

        feedback_prompt = ""
        if last_error:
            feedback_prompt = (
                "\n\n---\n"
                "**IMPORTANT:** Your previous attempt failed with a Liquid syntax error. "
                f"You MUST fix this specific issue: {last_error}\n"
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
            _validate_liquid_syntax(templated_html)

            logger.info("Successfully generated and validated template.")
            return templated_html.strip()

        except Exception as e:
            if type(e).__name__ == 'TemplateSyntaxError':
                logger.warning(f"Attempt {attempt + 1} failed validation. Error: {e}")
                last_error = e
            else:
                # It's a different, unexpected error
                logger.error(f"An unexpected error occurred during Liquid injection attempt {attempt + 1}: {e}", exc_info=True)
                raise ValueError(f"An unexpected error occurred during template generation: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during Liquid injection attempt {attempt + 1}: {e}", exc_info=True)
            raise ValueError(f"An unexpected error occurred during template generation: {e}")

    logger.error("Failed to generate a valid template after multiple retries.")
    raise ValueError(f"Failed to create a valid template after {max_retries} attempts. Last syntax error: {last_error}")
