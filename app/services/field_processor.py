import logfire
from typing import Any
from huggingface_hub import InferenceClient


from app.core.config import settings

client = InferenceClient(api_key=settings.HF_TOKEN)


def process_field_request(
    action: str,
    fieldName: str,
    originalText: str = "",
    instruction: str = "",
    tone: str = "professional",
    format: str | None = None,
    fullResumeData: dict[str, Any] | None = None,
) -> str:
    from app.utils.prompt_loader import load_prompt
    import json

    with logfire.span("process_field_request", action=action, field_name=fieldName):
        system_prompt = load_prompt("field_processor/system.md")

    # Prepare template blocks
    instructions_block = f"Instructions: {instruction}" if instruction else ""
    tone_block = f"Tone: {tone}" if tone else ""
    
    # Determine the target format and construct the format block dynamically
    if format:
        # User explicitly selected a format - command the LLM strictly to use it
        if format == "bullets":
            format_block = "Format: You MUST format the output strictly as a bulleted list using <ul> and <li> tags. Ignore the formatting style of the original text."
        else:
            format_block = "Format: You MUST format the output strictly as a paragraph. Ignore the formatting style of the original text."
    else:
        # No explicit format chosen - auto-detect and preserve the original format
        is_bullets = False
        if action == "REWRITE" and originalText:
            text_stripped = originalText.strip()
            if "<li>" in text_stripped or "<ul>" in text_stripped:
                is_bullets = True
            else:
                import re
                clean_text = re.sub(r'<[^>]+>', '\n', text_stripped)
                lines = [line.strip() for line in clean_text.split("\n") if line.strip()]
                bullet_chars = ["•", "-", "*", "–"]
                for line in lines:
                    if any(line.startswith(char) for char in bullet_chars):
                        is_bullets = True
                        break
        
        if is_bullets:
            format_block = "Format: The original text was bulleted. You MUST preserve this formatting and format the output as a bulleted list using <ul> and <li> tags."
        else:
            format_block = "Format: The original text was a paragraph. You MUST preserve this formatting and format the output as a paragraph."
    
    resume_context_block = ""
    if fullResumeData:
        # Create a simplified context from the resume data to avoid context window issues
        # and focus on the most relevant parts (experience, projects, skills)
        context_data = {
            "personalInfo": fullResumeData.get("personalInfo", {}),
            "experience": fullResumeData.get("sections", {}).get("experience", {}).get("items", []),
            "skills": fullResumeData.get("sections", {}).get("skills", {}).get("items", []),
            "projects": fullResumeData.get("sections", {}).get("projects", {}).get("items", []),
            "education": fullResumeData.get("sections", {}).get("education", {}).get("items", []),
        }
        resume_context_block = f"\n\nContext from entire resume:\n{json.dumps(context_data, indent=2)}"


    if action == "REWRITE":
        user_prompt_template = load_prompt("field_processor/rewrite.md")
        user_prompt = user_prompt_template.format(
            fieldName=fieldName,
            instructions_block=instructions_block,
            tone_block=tone_block,
            format_block=format_block,
            originalText=originalText,
            resume_context_block=resume_context_block
        )
    else:
        user_prompt_template = load_prompt("field_processor/generate.md")
        user_prompt = user_prompt_template.format(
            fieldName=fieldName,
            instructions_block=instructions_block,
            tone_block=tone_block,
            format_block=format_block,
            resume_context_block=resume_context_block
        )



    # Call the HuggingFace Inference API
    try:
        chat_completion = client.chat_completion(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=1024,
        )

        content = chat_completion.choices[0].message.content
        if content is None:
            logfire.warning("HF Inference API returned empty content")
            return ""
        
        logfire.info(f"Successfully processed {action} for {fieldName}")
        return content.strip()
    except Exception as e:
        logfire.error(f"HF Inference API call failed: {e}", error=str(e))
        raise e
