Generate content for a resume {fieldName} field.
{instructions_block}
{tone_block}
{format_block}
Length: Max 4 bullets or 3 sentences.
{resume_context_block}


Respond with ONLY the generated text.

### LLM SAFEGUARDS:
- Never invent numeric metrics, dates, certifications, or skills not present in the provided `resume_context_block`.
- If the context lacks evidence for a requested achievement or number, produce a high-quality phrasing without numeric quantification.
- Keep content strictly grounded in the provided context; when in doubt, prefer omission over fabrication.

