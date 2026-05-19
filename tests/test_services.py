from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.resume import ResumeData
from app.services.field_processor import process_field_request
from app.services.resume_processor import parse_resume, structure_resume_with_llm


@pytest.mark.asyncio
@patch("app.services.resume_processor.structured_parser")
async def test_structure_resume_with_llm(mock_parser):
    # Mock LLM response
    mock_resume_data = ResumeData(
        basics={"name": "John Doe", "email": "john@example.com", "phone": "", "location": "", "url": {"label": "", "href": ""}, "customFields": []},
        summary={"content": "Experienced developer", "visible": True},
        sections={}
    )
    mock_parser.ainvoke = AsyncMock(return_value=mock_resume_data)

    result = await structure_resume_with_llm("Raw resume text")
    
    assert isinstance(result, ResumeData)
    assert result.basics.name == "John Doe"
    mock_parser.ainvoke.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.resume_processor.ContentExtractor.extract_text_from_pdf")
@patch("app.services.resume_processor.structure_resume_with_llm")
@patch("app.services.resume_processor.is_valid_resume_file")
@patch("app.services.resume_processor.ContentExtractor.validate_content_quality")
async def test_parse_resume_pdf(mock_quality, mock_valid, mock_structure, mock_extract):
    mock_valid.return_value = (True, None)
    mock_extract.return_value = "Extracted text"
    mock_quality.return_value = True
    
    mock_resume_data = MagicMock(spec=ResumeData)
    mock_resume_data.model_dump.return_value = {"basics": {"name": "John Doe"}}
    mock_structure.return_value = mock_resume_data

    # Use a dummy filename that ends with .pdf
    result, text = await parse_resume(b"pdf_bytes", "test.pdf")

    assert isinstance(result, dict)
    assert result["basics"]["name"] == "John Doe"
    assert text == "Extracted text"

    mock_extract.assert_called_once()
    mock_structure.assert_called_once_with("Extracted text")

@patch("app.services.field_processor.client.chat_completion")
@patch("app.utils.prompt_loader.load_prompt")
def test_process_field_request_rewrite(mock_load_prompt, mock_chat):
    mock_load_prompt.return_value = "System prompt"
    # Mock HF response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Improved text"
    mock_chat.return_value = mock_response

    result = process_field_request(
        action="REWRITE",
        fieldName="Summary",
        originalText="old text",
        tone="professional"
    )

    assert result == "Improved text"
    mock_chat.assert_called_once()


@patch("app.services.field_processor.client.chat_completion")
@patch("app.utils.prompt_loader.load_prompt")
def test_process_field_request_formatting_detection(mock_load_prompt, mock_chat):
    mock_load_prompt.side_effect = lambda path: "Rewrite template {format_block}" if "rewrite" in path else "System prompt"
    
    # Mock HF response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Improved text"
    mock_chat.return_value = mock_response

    # Scenario 1: Original text is paragraph, format is None -> should default to paragraph
    process_field_request(
        action="REWRITE",
        fieldName="Summary",
        originalText="This is a simple paragraph.",
        format=None
    )
    called_user_prompt = mock_chat.call_args[1]["messages"][1]["content"]
    assert "Format: The original text was a paragraph. You MUST preserve this formatting and format the output as a paragraph." in called_user_prompt

    mock_chat.reset_mock()

    # Scenario 2: Original text contains HTML bullet list, format is None -> should detect bullets
    process_field_request(
        action="REWRITE",
        fieldName="Summary",
        originalText="<ul><li>First item</li><li>Second item</li></ul>",
        format=None
    )
    called_user_prompt = mock_chat.call_args[1]["messages"][1]["content"]
    assert "Format: The original text was bulleted. You MUST preserve this formatting and format the output as a bulleted list using <ul> and <li> tags." in called_user_prompt

    mock_chat.reset_mock()

    # Scenario 3: Original text has plain text bullets, format is None -> should detect bullets
    process_field_request(
        action="REWRITE",
        fieldName="Summary",
        originalText="• Led the development\n• Optimized database",
        format=None
    )
    called_user_prompt = mock_chat.call_args[1]["messages"][1]["content"]
    assert "Format: The original text was bulleted. You MUST preserve this formatting and format the output as a bulleted list using <ul> and <li> tags." in called_user_prompt

    mock_chat.reset_mock()

    # Scenario 4: User explicitly selected paragraph, but original was bullets -> should respect user choice
    process_field_request(
        action="REWRITE",
        fieldName="Summary",
        originalText="• Led the development\n• Optimized database",
        format="paragraph"
    )
    called_user_prompt = mock_chat.call_args[1]["messages"][1]["content"]
    assert "Format: You MUST format the output strictly as a paragraph. Ignore the formatting style of the original text." in called_user_prompt

    mock_chat.reset_mock()

    # Scenario 5: Original text has bullets but also introductory plain text, format is None -> should detect bullets
    process_field_request(
        action="REWRITE",
        fieldName="Summary",
        originalText="Key Highlights:\n- Developed microservices\n- Managed deployments",
        format=None
    )
    called_user_prompt = mock_chat.call_args[1]["messages"][1]["content"]
    assert "Format: The original text was bulleted. You MUST preserve this formatting and format the output as a bulleted list using <ul> and <li> tags." in called_user_prompt


@pytest.mark.asyncio
async def test_tailor_resume_invalid_jd():
    from app.services.tailor_service import tailor_resume
    from app.models.resume import ResumeData

    resume_data = ResumeData(
        basics={"name": "John Doe", "email": "john@example.com", "phone": "", "location": "", "url": {"label": "", "href": ""}, "customFields": []},
        summary={"content": "Experienced developer", "visible": True},
        sections={}
    )

    with pytest.raises(ValueError, match="The provided text does not appear to be a valid job description."):
        await tailor_resume(resume_data, "Invalid short JD text")


@pytest.mark.asyncio
async def test_tailor_resume_user_invalid_jd():
    from app.services.tailor_service import tailor_resume
    from app.models.resume import ResumeData

    resume_data = ResumeData(
        basics={"name": "John Doe", "email": "john@example.com", "phone": "", "location": "", "url": {"label": "", "href": ""}, "customFields": []},
        summary={"content": "Experienced developer", "visible": True},
        sections={}
    )

    invalid_jd = (
        "3 Tips to Make the 8B Approach ViableEnforce Max Tokens = 50: "
        "Since you only need a tiny JSON object back, cap the max_tokens parameter on the API call. "
        "This prevents the model from rambling and keeps your latency as low as possible."
        "Use JSON Mode / Structured Outputs: Tools like Ollama, vLLM, or Groq allow you to enforce a JSON schema. "
        "Use this so your backend code can safely parse the response (response.is_valid) without crashing."
        "Set Temperature to 0: You want completely predictable, deterministic validation."
        "Would you like help writing the Python or Node.js code to process this JSON validation pipeline, "
        "or should we look into optimizing the prompt for your exact business use case?"
    )

    with pytest.raises(ValueError, match="The provided text does not appear to be a valid job description."):
        await tailor_resume(resume_data, invalid_jd)
