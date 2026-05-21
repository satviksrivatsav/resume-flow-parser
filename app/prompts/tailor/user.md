### JOB DESCRIPTION
{job_description}

### RESUME SECTIONS TO TAILOR
{sections_json}

Please tailor the above sections to the job description. Return the result as a JSON object where the keys are the section IDs and the values are the tailored content for those sections.
For each section, ensure the structure remains identical to the input, including UUIDs and any nested objects.

Tailored JSON:

### IMPORTANT INSTRUCTIONS FOR TAILORING:
- Do NOT add skills, tools, certifications, dates, or metrics that are not explicitly present in the `sections_json` input. If the JD asks for a skill the candidate lacks, do NOT add it to the tailored sections; instead include a clear suggestion (e.g., "Consider gaining experience with X") in the output suggestions field.
- Preserve all UUIDs, titles, dates, and company names exactly as provided; only modify allowed fields (`summary`, `bullets`, `keywords`, etc.).
- Return only valid JSON matching the input structure; do not include explanatory text.
