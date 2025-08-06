import pytest
import io
import os
import json
from unittest.mock import patch, MagicMock, mock_open

# Ensure the app path is in the python path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from renderer import render_html_to_pdf
from content_extractor import extract_json_from_cv
from template_builder import create_template_from_docx

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


@patch('template_builder._get_cached_html', return_value=None)
@patch('template_builder._cache_html')
@patch('httpx.Client')
@patch('template_builder.OpenAI')
@patch('template_builder._validate_liquid_template')
def test_template_creation_pipeline_from_docx_dom_aware(
    mock_validate_liquid, mock_openai, mock_httpx_client_constructor, mock_cache_html, mock_get_cached_html
):
    """
    End-to-end test for the DOM-aware template creation workflow.
    This test verifies that the system correctly uses BeautifulSoup to inject placeholders
    and validates the final template.
    """
    # Arrange
    # --- Mock Convertio API responses ---
    mock_start_response = MagicMock()
    mock_start_response.json.return_value = {"status": "ok", "data": {"id": "test_id"}}
    mock_status_finished_response = MagicMock()
    mock_status_finished_response.json.return_value = {
        "status": "ok",
        "data": {"step": "finish", "output": {"url": "http://fake.url/output.html"}}
    }
    # This HTML has intentionally separated spans that the old .replace() method would fail on.
    mock_download_response = MagicMock()
    mock_download_response.text = "<html><body><p><span>John</span> <span>Doe</span></p><p>Software Engineer</p></body></html>"

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_start_response
    mock_client_instance.get.side_effect = [mock_status_finished_response, mock_download_response]
    mock_httpx_client_constructor.return_value.__enter__.return_value = mock_client_instance

    # --- Mock OpenAI response (returns a replacement map) ---
    replacement_map = {
        "John Doe": "{{ name }}",
        "Software Engineer": "{{ title }}"
    }
    mock_llm_response = MagicMock()
    mock_llm_response.choices[0].message.content = json.dumps(replacement_map)
    mock_openai.return_value.chat.completions.create.return_value = mock_llm_response

    # --- Prepare input file ---
    docx_stream = io.BytesIO(b"dummy docx content")
    file_hash = "some_hash"
    with patch('template_builder._get_file_hash', return_value=file_hash):
        # Act
        final_template = create_template_from_docx(docx_stream, "test.docx")

    # Assert
    # Verify that the text extraction for the LLM still works as expected
    llm_prompt_text = mock_openai.return_value.chat.completions.create.call_args[1]['messages'][1]['content']
    assert "John\nDoe\nSoftware Engineer" in llm_prompt_text

    # Verify that the final output is correctly assembled using the DOM-aware method.
    # Note: The output will have the placeholder replacing the text within the spans.
    expected_html = '<html><body><p><span>{{ name }}</span> <span>{{ name }}</span></p><p>{{ title }}</p></body></html>'
    assert final_template == expected_html

    # Verify that the final template was validated
    mock_validate_liquid.assert_called_once_with(expected_html)


# --- Tests for Caching Logic ---

@patch('template_builder._get_cached_html', return_value=None)
@patch('template_builder._cache_html')
@patch('template_builder._start_conversion', return_value='test_conversion_id')
@patch('template_builder._poll_conversion_status', return_value='http://fake.url/output.html')
@patch('template_builder._download_html_content', return_value='<html><body><p>Jane Doe</p></body></html>')
@patch('template_builder._get_replacement_map_from_llm', return_value={'Jane Doe': '{{ name }}'})
def test_template_creation_with_cache_miss(
    mock_get_map, mock_download, mock_poll, mock_start, mock_cache_html, mock_get_cached_html
):
    """
    Tests the template creation workflow when the item is NOT in the cache.
    It should call the full conversion pipeline and then cache the result.
    """
    # Arrange
    docx_stream = io.BytesIO(b"new dummy docx content")
    filename = "new_test.docx"
    file_hash = "a_mock_hash_would_be_here" # In a real test, we might calculate this

    with patch('template_builder._get_file_hash', return_value=file_hash):
        # Act
        final_template = create_template_from_docx(docx_stream, filename)

        # Assert
        # 1. Check if cache was consulted
        mock_get_cached_html.assert_called_once_with(file_hash)

        # 2. Check if the conversion process was triggered
        mock_start.assert_called_once()
        mock_poll.assert_called_once_with('test_conversion_id')
        mock_download.assert_called_once_with('http://fake.url/output.html')

        # 3. Check if the result was cached
        mock_cache_html.assert_called_once_with(file_hash, '<html><body><p>Jane Doe</p></body></html>')

        # 4. Check the final output
        assert final_template == "<html><body><p>{{ name }}</p></body></html>"


@patch('template_builder._get_cached_html', return_value='<html><body><p>Cached Content</p></body></html>')
@patch('template_builder._cache_html')
@patch('template_builder._start_conversion')
@patch('template_builder._get_replacement_map_from_llm', return_value={'Cached Content': '{{ name }}'})
def test_template_creation_with_cache_hit(
    mock_get_map, mock_start, mock_cache_html, mock_get_cached_html
):
    """
    Tests the template creation workflow when the item IS in the cache.
    It should NOT call the conversion pipeline and should use the cached HTML.
    """
    # Arrange
    docx_stream = io.BytesIO(b"cached dummy docx content")
    filename = "cached_test.docx"
    file_hash = "a_cached_hash"

    with patch('template_builder._get_file_hash', return_value=file_hash):
        # Act
        final_template = create_template_from_docx(docx_stream, filename)

        # Assert
        # 1. Check if cache was consulted
        mock_get_cached_html.assert_called_once_with(file_hash)

        # 2. Check that the conversion process was SKIPPED
        mock_start.assert_not_called()

        # 3. Check that the cache write was SKIPPED
        mock_cache_html.assert_not_called()

        # 4. Check that the LLM was still called with the cached content
        mock_get_map.assert_called_once_with('<html><body><p>Cached Content</p></body></html>')

        # 5. Check the final output
        assert final_template == "<html><body><p>{{ name }}</p></body></html>"
