import pytest
import io
import os
from unittest.mock import patch, MagicMock, mock_open

# Ensure the app path is in the python path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from renderer import render_html_to_pdf
from content_extractor import extract_json_from_cv
from template_builder import create_template_from_pdf

# --- Test for Renderer (Fix Verification) ---

@patch("builtins.open", new_callable=mock_open, read_data="<h1>Hello, {{ name }}</h1><p>Skills: {{ skills | join: ', ' }}</p>")
def test_render_html_to_pdf_with_liquid_syntax(mock_file):
    """
    Tests that the renderer correctly processes a template with Liquid syntax.
    This verifies that the switch from Jinja2 to liquidpy was successful.
    """
    # Arrange
    json_data = {
        "name": "John Doe",
        "skills": ["Python", "FastAPI", "Testing"]
    }

    # Act
    pdf_stream = render_html_to_pdf("any_template_name.html", json_data)

    # Assert
    mock_file.assert_called_with(os.path.join('templates/html', 'any_template_name.html'), 'r', encoding='utf-8')
    assert isinstance(pdf_stream, io.BytesIO)
    pdf_content = pdf_stream.read()
    assert pdf_content.startswith(b'%PDF-')
    assert len(pdf_content) > 100

# --- Mocked Integration Tests for the Full Pipeline ---

@patch('content_extractor.convert_from_bytes')
@patch('content_extractor.pytesseract')
@patch('content_extractor.OpenAI')
@patch("builtins.open", new_callable=mock_open, read_data="<h1>{{ name }}</h1><h2>{{ title }}</h2>")
@patch('renderer.HTML')
def test_anonymization_pipeline_pdf_input(mock_weasyprint_html, mock_file, mock_openai, mock_pytesseract, mock_convert_from_bytes):
    """
    End-to-end test for the CV anonymization workflow (Workflow 2) with a PDF input.
    Mocks all external dependencies.
    """
    # Arrange
    # Mock the dependencies for PDF processing
    mock_convert_from_bytes.return_value = [MagicMock()] # Return a list with one mock image
    mock_pytesseract.image_to_string.return_value = "Extracted text from PDF"

    # Mock OpenAI client and its response
    mock_chat_completion = MagicMock()
    mock_chat_completion.choices[0].message.content = '{"name": "Mocked Name", "title": "Mocked Title"}'
    mock_openai.return_value.chat.completions.create.return_value = mock_chat_completion

    # Create a dummy CV file stream
    dummy_cv_content = b"This is a dummy PDF file."
    cv_stream = io.BytesIO(dummy_cv_content)

    # Act
    # 1. Extract JSON from CV
    json_data = extract_json_from_cv(cv_stream, "application/pdf")

    # 2. Render to PDF
    render_html_to_pdf('professional_template.html', json_data)

    # Assert
    # Check that PDF processing was triggered
    mock_convert_from_bytes.assert_called_once()
    mock_pytesseract.image_to_string.assert_called_once()

    # Check that OpenAI was called with the text from OCR
    mock_openai.return_value.chat.completions.create.assert_called_once()
    user_prompt = mock_openai.return_value.chat.completions.create.call_args[1]['messages'][1]['content']
    assert "Extracted text from PDF" in user_prompt

    # Check the final JSON data
    assert json_data['name'] == 'Mocked Name'

    # Check that the renderer was called correctly
    mock_file.assert_called_with(os.path.join('templates/html', 'professional_template.html'), 'r', encoding='utf-8')
    mock_weasyprint_html.assert_called_with(string='<h1>Mocked Name</h1><h2>Mocked Title</h2>')


@patch('template_builder.OpenAI')
def test_template_creation_pipeline(mock_openai):
    """
    End-to-end test for the template creation workflow (Workflow 1).
    Mocks the external dependency (OpenAI).
    """
    # Arrange
    # Mock the two OpenAI calls made in this workflow
    mock_pdf_to_html_response = MagicMock()
    mock_pdf_to_html_response.choices[0].message.content = "<h1>Hello, World</h1>"

    mock_html_to_liquid_response = MagicMock()
    mock_html_to_liquid_response.choices[0].message.content = "<h1>Hello, {{ name }}</h1>"

    mock_openai.return_value.chat.completions.create.side_effect = [
        mock_pdf_to_html_response,
        mock_html_to_liquid_response
    ]

    # Create a dummy PDF file stream and mock the PDF-to-image conversion
    with patch('template_builder.convert_from_bytes') as mock_convert:
        mock_convert.return_value = [MagicMock()] # Return a list with one mock image
        pdf_stream = io.BytesIO(b"dummy pdf bytes")

        # Act
        html_template = create_template_from_pdf(pdf_stream)

    # Assert
    assert mock_openai.return_value.chat.completions.create.call_count == 2
    assert html_template == "<h1>Hello, {{ name }}</h1>"
