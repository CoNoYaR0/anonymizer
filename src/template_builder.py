import os
import hashlib
import requests
from typing import Optional
from dotenv import load_dotenv

# Import caching functions from the database module
from . import database

# Load environment variables
load_dotenv()
CONVERTIO_API_KEY = os.getenv("CONVERTIO_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def _calculate_file_hash(file_content: bytes) -> str:
    """
    Calculates the SHA-256 hash of the file content.

    Args:
        file_content: The binary content of the file.

    Returns:
        The hex digest of the SHA-256 hash.
    """
    # TODO: Implement the hashing logic.
    sha256_hash = hashlib.sha256()
    sha256_hash.update(file_content)
    return sha256_hash.hexdigest()


def _convert_docx_to_html(file_path: str) -> str:
    """
    Converts a DOCX file to HTML using the Convertio API.

    Args:
        file_path: The path to the DOCX file.

    Returns:
        The converted HTML content as a string.

    Raises:
        Exception: If the Convertio API key is missing or the conversion fails.
    """
    if not CONVERTIO_API_KEY:
        raise Exception("CONVERTIO_API_KEY is not set.")

    # TODO: Implement the full Convertio API workflow.
    # 1. Upload the file to Convertio.
    # 2. Start the conversion process.
    # 3. Poll for completion status.
    # 4. Download the resulting HTML content.

    print(f"TODO: Calling Convertio API to convert {file_path}")

    # Placeholder return value
    return "<html><body><h1>Placeholder HTML</h1><p>This is content from a DOCX.</p></body></html>"


def _inject_liquid_placeholders(html_content: str) -> str:
    """
    Uses an LLM to intelligently replace static text in HTML with Liquid placeholders.

    Args:
        html_content: The HTML string to process.

    Returns:
        An HTML string with Liquid placeholders (e.g., {{ name }}) injected.

    Raises:
        Exception: If the OpenAI API key is missing.
    """
    if not OPENAI_API_KEY:
        raise Exception("OPENAI_API_KEY is not set.")

    # TODO: Implement the LLM processing logic.
    # 1. Use BeautifulSoup to parse the HTML and extract text nodes.
    # 2. Construct a prompt for the LLM (e.g., GPT-4o) asking it to identify
    #    which pieces of text are dynamic data (like names, dates, job titles)
    #    and suggest appropriate Liquid variable names.
    # 3. Parse the LLM's response.
    # 4. Use BeautifulSoup again to replace the original text nodes with the
    #    corresponding Liquid placeholders, ensuring the HTML structure remains intact.

    print("TODO: Calling OpenAI API to inject Liquid placeholders.")

    # Placeholder return value
    return html_content.replace("Placeholder HTML", "<h1>{{ document_title }}</h1>")


def create_template_from_docx(file_path: str, file_content: bytes) -> str:
    """
    Orchestrates the full workflow for creating a template from a DOCX file.

    Args:
        file_path: The path to the uploaded DOCX file.
        file_content: The binary content of the DOCX file.

    Returns:
        The final HTML/Liquid template as a string.
    """
    # 1. Calculate the file hash
    file_hash = _calculate_file_hash(file_content)
    print(f"Calculated hash for {file_path}: {file_hash}")

    # 2. Check the cache
    cached_html = database.get_cached_html(file_hash)
    if cached_html:
        print("Found pre-converted HTML in cache.")
        html_content = cached_html
    else:
        print("HTML not in cache. Converting with Convertio...")
        # 3. If not cached, convert the DOCX to HTML
        html_content = _convert_docx_to_html(file_path)

        # 4. Cache the newly converted HTML
        database.cache_html(file_hash, html_content)
        print("Saved new HTML to cache.")

    # 5. Inject Liquid placeholders into the HTML
    print("Injecting Liquid placeholders...")
    liquid_template = _inject_liquid_placeholders(html_content)

    print("Template creation process complete.")
    return liquid_template
