import io
import logging
import base64
from typing import IO
from openai import OpenAI

# Configure logger
logger = logging.getLogger(__name__)

def _pdf_to_html(file_stream: IO[bytes]) -> str:
    """
    Converts a PDF file stream to a single HTML string with inline CSS
    using a multimodal LLM.
    """
    logger.info("Sending PDF to vision-capable LLM for HTML conversion.")
    pdf_base64 = base64.b64encode(file_stream.read()).decode('utf-8')
    client = OpenAI()

    system_prompt = """
You are an expert web developer. Your task is to look at an image of a CV page and perfectly replicate its layout and content as a single, clean HTML file with inline CSS.

**Rules:**
1.  You MUST use inline CSS for styling (e.g., `<p style="color: blue;">`).
2.  The output MUST be a single, complete HTML string.
3.  Do not include any commentary or explanation outside of the HTML code.
4.  Replicate the text content and layout as precisely as possible.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please convert this CV page into a single HTML file with inline CSS."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:application/pdf;base64,{pdf_base64}"
                            }
                        }
                    ]
                }
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
