Parse this resume and return structured JSON:

---
{raw_text}
---

Return only valid JSON, no markdown formatting.

### INSTRUCTIONS:
- Only extract information explicitly present in the resume text. Do NOT infer or invent dates, roles, scores, or skills.
- If a field cannot be determined from the text, use an empty string, `null`, or an empty array as required by the schema.
- Return exactly the JSON schema described in the system prompt; do not add extra keys or commentary.
