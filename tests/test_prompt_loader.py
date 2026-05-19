
import pytest

from app.utils.prompt_loader import load_prompt


def test_load_prompt_success():
    # Test loading an existing prompt
    # resume_parser/system.md should exist
    content = load_prompt("resume_parser/system.md")
    assert "resume parsing expert" in content.lower()
    assert "JSON object" in content

def test_load_prompt_not_found():
    # Test loading a non-existent prompt
    with pytest.raises(FileNotFoundError):
        load_prompt("non_existent_prompt.md")

def test_load_prompt_field_processor():
    # Test loading field processor prompts
    content = load_prompt("field_processor/system.md")
    assert "minimalist resume writer" in content.lower()
