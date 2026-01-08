import fitz  # PyMuPDF
import json
import re
from huggingface_hub import InferenceClient
from app.core.config import settings
from typing import Any
import logging

logger = logging.getLogger(__name__)
client = InferenceClient(api_key=settings.HF_TOKEN)


async def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text content from PDF bytes using PyMuPDF."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_content = []
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text("text")
            text_content.append(text)
        
        doc.close()
        return "\n\n".join(text_content)
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise ValueError(f"Failed to extract text from PDF: {e}")


async def structure_resume_with_llm(raw_text: str) -> dict[str, Any]:
    """Use LLM to extract structured resume data from raw text."""
    
    system_prompt = """You are a resume parsing expert. Extract structured data from the resume text.

Return a JSON object with EXACTLY this structure:
{
  "personalInfo": {
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "+1234567890",
    "location": "City, State",
    "linkedin": "linkedin.com/in/profile",
    "website": "website.com",
    "github": "github.com/username",
    "summary": "Professional summary paragraph"
  },
  "education": [
    {
      "id": "uuid-string",
      "school": "University Name",
      "degree": "Bachelor of Science",
      "field": "Computer Science",
      "startDate": "2018-08",
      "endDate": "2022-05",
      "gpa": "3.8",
      "description": "Relevant coursework, honors, etc."
    }
  ],
  "workExperience": [
    {
      "id": "uuid-string",
      "company": "Company Name",
      "position": "Job Title",
      "location": "City, State",
      "startDate": "2022-06",
      "endDate": "2024-01",
      "current": false,
      "description": "• Bullet point achievements\\n• Another achievement"
    }
  ],
  "projects": [
    {
      "id": "uuid-string",
      "name": "Project Name",
      "technologies": "React, Node.js, PostgreSQL",
      "startDate": "2023-01",
      "endDate": "2023-06",
      "description": "What the project does and your contributions",
      "link": "github.com/user/project"
    }
  ],
  "skills": [
    {
      "id": "uuid-string",
      "category": "Programming Languages",
      "items": "Python, JavaScript, TypeScript, Go"
    },
    {
      "id": "uuid-string",
      "category": "Frameworks",
      "items": "React, FastAPI, Django"
    }
  ],
  "customSections": []
}

RULES:
- Generate unique UUIDs for each id field
- Use YYYY-MM format for dates
- If a field is not found, use empty string ""
- For current jobs, set "current": true and "endDate": ""
- Preserve bullet points in descriptions using \\n
- Extract ALL work experience, education, and projects found
- Group skills by logical categories"""

    user_prompt = f"""Parse this resume and return structured JSON:

---
{raw_text}
---

Return only valid JSON, no markdown formatting."""

    try:
        response = client.chat.completions.create(
            model="meta-llama/Llama-3.1-8B-Instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=4096
        )
        
        raw_content = response.choices[0].message.content if response.choices else None
        
    except Exception as e:
        logger.error(f"LLM API call failed: {e}")
        raise ValueError(f"LLM API call failed: {e}")
    
    try:
        if not raw_content:
            raise ValueError("LLM returned empty content")
        
        # Strip markdown code fences if present
        cleaned_content = raw_content.strip()
        if cleaned_content.startswith("```json"):
            cleaned_content = cleaned_content[7:]
        elif cleaned_content.startswith("```"):
            cleaned_content = cleaned_content[3:]
        if cleaned_content.endswith("```"):
            cleaned_content = cleaned_content[:-3]
        cleaned_content = cleaned_content.strip()
        
        # Extract only the JSON object (handle extra text after closing brace)
        # Find the first { and its matching }
        start_idx = cleaned_content.find('{')
        if start_idx == -1:
            raise ValueError("No JSON object found in response")
        
        # Count braces to find matching closing brace
        brace_count = 0
        end_idx = start_idx
        for i, char in enumerate(cleaned_content[start_idx:], start=start_idx):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i
                    break
        
        json_str = cleaned_content[start_idx:end_idx + 1]
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"LLM returned invalid JSON: {e}")
        raise ValueError("Failed to parse LLM response")


async def parse_resume_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    """Main entry point: PDF bytes → structured resume data."""
    
    # Step 1: Extract raw text
    raw_text = await extract_text_from_pdf(pdf_bytes)
    
    if not raw_text.strip():
        raise ValueError("Could not extract any text from PDF")
    
    # Step 2: Structure with LLM
    resume_data = await structure_resume_with_llm(raw_text)
    
    return resume_data
