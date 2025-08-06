import pytest
import io
import os
from unittest.mock import patch, MagicMock, mock_open

# Ensure the app path is in the python path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from renderer import render_html_to_pdf
from content_extractor import extract_json_from_cv
from template_builder import create_template_from_docx # Updated import

# --- Test for Renderer (Fix Verification) ---

@patch("builtins.open", new_callable=mock_open, read_data="<h1>Hello, {{ name }}</h1><p>Skills: {{ skills | join: ', ' }}</p>")
def test_render_html_to_pdf_with_liquid_syntax(mock_file):
    """
    Tests that the renderer correctly processes a template with Liquid syntax.
    """
    json_data = {"name": "John Doe", "skills": ["Python", "FastAPI", "Testing"]}
    pdf_stream = render_html_to_pdf("any_template_name.html", json_data)
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
    """
    # Arrange
    mock_convert_from_bytes.return_value = [MagicMock()]
    mock_pytesseract.image_to_string.return_value = "Extracted text from PDF"
    mock_chat_completion = MagicMock()
    mock_chat_completion.choices[0].message.content = '{"name": "Mocked Name", "title": "Mocked Title"}'
    mock_openai.return_value.chat.completions.create.return_value = mock_chat_completion
    cv_stream = io.BytesIO(b"This is a dummy PDF file.")

    # Act
    json_data = extract_json_from_cv(cv_stream, "application/pdf")
    render_html_to_pdf('professional_template.html', json_data)

    # Assert
    mock_pytesseract.image_to_string.assert_called_once()
    assert json_data['name'] == 'Mocked Name'
    mock_weasyprint_html.assert_called_with(string='<h1>Mocked Name</h1><h2>Mocked Title</h2>')


@patch('httpx.Client')
@patch('template_builder.OpenAI')
def test_template_creation_pipeline_from_docx(mock_openai, mock_httpx_client_constructor):
    """
    End-to-end test for the new template creation workflow using Convertio.
    Mocks the external dependencies (Convertio API via httpx, and OpenAI).
    """
    # Arrange
    # --- Mock the Convertio API responses ---
    mock_start_response = MagicMock()
    mock_start_response.status_code = 200
    mock_start_response.json.return_value = {
        "status": "ok",
        "data": {"id": "test_conversion_id"}
    }

    mock_status_pending_response = MagicMock()
    mock_status_pending_response.status_code = 200
    mock_status_pending_response.json.return_value = {
        "status": "ok",
        "data": {"step": "convert", "step_percent": 50}
    }

    mock_status_finished_response = MagicMock()
    mock_status_finished_response.status_code = 200
    mock_status_finished_response.json.return_value = {
        "status": "ok",
        "data": {
            "step": "finish",
            "step_percent": 100,
            "output": {"url": "http://fake.convertio.url/output.html"}
        }
    }

    mock_download_response = MagicMock()
    mock_download_response.status_code = 200
    mock_download_response.text = "<h1>Raw HTML from Convertio</h1>"

    # Configure the mock client instance to return the sequence of responses
    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_start_response
    mock_client_instance.get.side_effect = [
        mock_status_pending_response,
        mock_status_finished_response,
        mock_download_response
    ]
    mock_httpx_client_constructor.return_value.__enter__.return_value = mock_client_instance

    # --- Mock the OpenAI response for Liquid injection ---
    mock_llm_response = MagicMock()
    mock_llm_response.choices[0].message.content = "<h1>{{ title }}</h1>"
    mock_openai.return_value.chat.completions.create.return_value = mock_llm_response

    # --- Prepare input file ---
    docx_stream = io.BytesIO(b"dummy docx content")

    # Act
    final_template = create_template_from_docx(docx_stream, "test.docx")

    # Assert
    # Verify Convertio calls
    assert mock_client_instance.post.call_count == 1
    assert mock_client_instance.get.call_count == 3 # status pending, status finished, download

    # Verify OpenAI call
    mock_openai.return_value.chat.completions.create.assert_called_once()
    llm_prompt_html = mock_openai.return_value.chat.completions.create.call_args[1]['messages'][1]['content']
    assert "<h1>Raw HTML from Convertio</h1>" in llm_prompt_html

    # Verify final output
    assert final_template == "<h1>{{ title }}</h1>"
