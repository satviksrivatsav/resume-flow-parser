import json
import logfire
import copy
from typing import Any, Dict, List, Optional
from langchain_groq import ChatGroq
from app.models.resume import ResumeData
from app.models.tailor import TailoredSection, TailorResponse
from app.utils.prompt_loader import load_prompt

from pydantic import BaseModel, Field

# Initialize the Langchain LLM Client
tailor_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3  # Slightly higher temperature for creative rephrasing
)

class JDValidation(BaseModel):
    is_valid: bool = Field(description="True if the text is a valid job description or contains details of a job role, False otherwise.")
    reason: str = Field(description="Brief reason for the validation result.")

validator_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.0,
    max_tokens=150
)

structured_validator = validator_llm.with_structured_output(JDValidation)

def merge_tailored_section(section_id: str, original: dict, tailored: dict) -> dict:
    """Strictly merge only allowed description/content fields from the AI's response."""
    merged = copy.deepcopy(original)
    
    if section_id == "summary":
        if isinstance(tailored, dict) and "content" in tailored:
            merged["content"] = tailored["content"]
        elif isinstance(tailored, str):
            merged["content"] = tailored
        return merged
    
    if section_id == "headline":
        if isinstance(tailored, dict) and "headline" in tailored:
            return {"headline": tailored["headline"]}
        elif isinstance(tailored, str):
            return {"headline": tailored}
        return merged
        
    if "items" in merged and isinstance(tailored, dict) and "items" in tailored:
        for i, orig_item in enumerate(merged["items"]):
            if i < len(tailored["items"]):
                tail_item = tailored["items"][i]
                if not isinstance(tail_item, dict):
                    continue
                
                allowed_item_fields = ["summary", "description", "bullets", "name", "keywords"]
                
                for field in allowed_item_fields:
                    if field in tail_item:
                        orig_item[field] = tail_item[field]
                        
    return merged

async def tailor_resume(
    resume_data: ResumeData, 
    job_description: str, 
    sections_to_tailor: Optional[List[str]] = None
) -> TailorResponse:
    """
    Tailor specific resume sections based on a job description.
    """
    # Use LLM power to validate the job description
    try:
        validation_system_prompt = load_prompt("tailor/validate_jd.md")
        messages = [
            {"role": "system", "content": validation_system_prompt},
            {"role": "user", "content": f"Please validate the following text:\n\n{job_description}"}
        ]
        
        # Invoke the llama-3.1-8b-instant validator
        validation_result = structured_validator.invoke(messages)
        logfire.info("Job description LLM validation outcome", is_valid=validation_result.is_valid, reason=validation_result.reason)
        
        if not validation_result.is_valid:
            logfire.warning(f"Job description validation failed: {validation_result.reason}")
            raise ValueError("The provided text does not appear to be a valid job description.")
            
    except ValueError:
        raise
    except Exception as e:
        logfire.error(f"Error during job description LLM validation: {e}", error=str(e))
        # Simple length fallback in case of LLM API issues to keep the service resilient
        if not job_description or len(job_description.strip()) < 100:
            logfire.warning("Job description fallback validation failed")
            raise ValueError("The provided text does not appear to be a valid job description.")

    with logfire.span("tailor_resume", sections=sections_to_tailor):
        sections_to_process = {}
        
        # Mapping of standard section keys to their display names
        section_display_names = {
            "summary": "Professional Summary",
            "headline": "Headline",
            "experience": "Work Experience",
            "education": "Education",
            "projects": "Projects",
            "skills": "Skills",
            "awards": "Awards",
            "certifications": "Certifications",
            "publications": "Publications",
            "volunteer": "Volunteer",
            "references": "References",
        }

        # If none specified, we'll default to the ones provided in the request
        # But here we assume the frontend sent a valid list
        if not sections_to_tailor:
            sections_to_tailor = ["summary", "headline", "experience", "projects", "skills"]

        # Extract Summary
        if "summary" in sections_to_tailor and resume_data.summary.content:
            sections_to_process["summary"] = resume_data.summary.model_dump()

        # Extract Headline
        if "headline" in sections_to_tailor and resume_data.basics.headline:
            sections_to_process["headline"] = {"headline": resume_data.basics.headline}
        
        # Extract Standard Sections
        for field_name, section in resume_data.sections:
            if field_name in sections_to_tailor and hasattr(section, 'items') and len(section.items) > 0:
                sections_to_process[field_name] = section.model_dump()

        # Extract Custom Sections
        for section in resume_data.customSections:
            if section.id in sections_to_tailor and len(section.items) > 0:
                sections_to_process[section.id] = section.model_dump()
                # Store the custom name for display later
                section_display_names[section.id] = section.name

        if not sections_to_process:
            logfire.warning("No valid sections found to tailor")
            return TailorResponse(tailoredSections=[])

        # Prepare prompts
        system_prompt = load_prompt("tailor/system.md")
        user_prompt_template = load_prompt("tailor/user.md")
        user_prompt = user_prompt_template.format(
            job_description=job_description,
            sections_json=json.dumps(sections_to_process, indent=2)
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            logfire.info(f"Sending tailoring request for {len(sections_to_process)} sections")
            response = await tailor_llm.ainvoke(messages)
            
            # Parse the JSON response
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            tailored_data = json.loads(content)
            
            # Map back to TailoredSection models
            result_sections = []
            for section_id, tailored_content in tailored_data.items():
                original_content = sections_to_process.get(section_id)
                if not original_content:
                    continue
                
                section_name = section_display_names.get(section_id, section_id.capitalize())
                
                merged_content = merge_tailored_section(section_id, original_content, tailored_content)
                
                result_sections.append(TailoredSection(
                    sectionId=section_id,
                    sectionName=section_name,
                    originalContent=original_content,
                    tailoredContent=merged_content
                ))
                
            return TailorResponse(tailoredSections=result_sections)
            
        except Exception as e:
            logfire.error(f"Tailoring LLM call failed: {e}", error=str(e))
            raise ValueError(f"Tailoring failed: {e}") from e
