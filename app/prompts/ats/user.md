Analyze the following resume and return the ATS report.

### Parsed Resume JSON:
{parsed_data}

### Raw Resume Text:
{raw_text}

{job_description_section}

### IMPORTANT INSTRUCTIONS FOR THE LLM:
- DO NOT INVENT or GUESS any skills, dates, metrics, certifications, or job titles. Only use values present in the provided parsed JSON or raw text.
- If a Job Description is not provided, set `jd_match` to `null` in the output JSON and do not attempt to match against any default role.
- When a required output field cannot be populated from the input, return an explicit empty value (empty string, `null`, or `[]`) as appropriate — do NOT fabricate placeholder numbers or percentages.
- Return only valid JSON that conforms to the `ats` system schema; no commentary, no additional text.
