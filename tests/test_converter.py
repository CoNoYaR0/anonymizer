import pytest
from fastapi.testclient import TestClient
import docx
import io

# Import the FastAPI app instance from your main application file
from main import app

# Create a client for testing
client = TestClient(app)

@pytest.fixture
def sample_docx_stream() -> io.BytesIO:
    """
    Creates a sample .docx file in memory with placeholder text
    and returns it as a BytesIO stream.
    """
    document = docx.Document()
    document.add_heading('CV of Jean Dupont', level=1)
    document.add_paragraph("This CV belongs to Jean Dupont.")
    document.add_paragraph(
        "Contact: jean.dupont@email.com or call 01 23 45 67 89."
    )
    document.add_paragraph(
        "I am a skilled professional living in Paris."
    )
    document.add_paragraph(
        "My friend, Marie Curie, also recommends me."
    )

    # Save the document to a byte stream
    stream = io.BytesIO()
    document.save(stream)
    stream.seek(0)
    return stream

def test_convert_to_template_endpoint_success(sample_docx_stream: io.BytesIO, monkeypatch):
    """
    Tests the /convert-to-template endpoint with a valid .docx file,
    mocking the LLM call to ensure deterministic results.
    """
    # 1. Define the mock function and its return value
    mock_semantic_map = {
        "Jean Dupont": "{{ name }}",
        "Marie Curie": "{{ person }}",
        "jean.dupont@email.com": "{{ email }}",
        "01 23 45 67 89": "{{ phone }}",
        "Paris": "{{ location }}"
    }

    def mock_get_map_from_llm(text: str):
        # In a real test, you might want to return a more complex
        # object here to test block replacements. For now, this is fine.
        return {
            "simple_replacements": mock_semantic_map,
            "block_replacements": []
        }

    # 2. Apply the mock to the Stage 1 and Stage 3 functions
    monkeypatch.setattr(
        "docx_to_template_converter._get_semantic_map_from_llm",
        mock_get_map_from_llm
    )
    monkeypatch.setattr(
        "main.validate_template_with_llm",
        lambda docx_stream: {"is_valid": True, "issues": []}
    )

    # 3. Run the test with the mock in place
    files = {'file': ('sample_cv.docx', sample_docx_stream, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
    response = client.post("/convert-to-template", files=files)

    # --- Assertions ---
    assert response.status_code == 200
    assert 'attachment; filename="sample_cv_template.docx"' in response.headers['content-disposition']

    # Read the content of the response
    response_stream = io.BytesIO(response.content)
    returned_doc = docx.Document(response_stream)

    returned_text = "\n".join([p.text for p in returned_doc.paragraphs])
    print(f"Returned text:\n---\n{returned_text}\n---")

    # Check for placeholder replacement
    assert "{{ name }}" in returned_text
    assert "{{ email }}" in returned_text
    assert "{{ phone }}" in returned_text
    assert "{{ location }}" in returned_text
    assert "{{ person }}" in returned_text

    # Check that original data is gone
    assert "Jean Dupont" not in returned_text
    assert "jean.dupont@email.com" not in returned_text
    assert "01 23 45 67 89" not in returned_text
    assert "Paris" not in returned_text
    assert "Marie Curie" not in returned_text

def test_convert_to_template_endpoint_invalid_file_type():
    """
    Tests the /convert-to-template endpoint with an invalid file type.
    """
    # Create a dummy text file
    txt_stream = io.BytesIO(b"this is not a docx file")
    files = {'file': ('test.txt', txt_stream, 'text/plain')}

    response = client.post("/convert-to-template", files=files)

    assert response.status_code == 400
    assert response.json() == {"error": "Invalid file type. Please upload a valid .docx file."}
