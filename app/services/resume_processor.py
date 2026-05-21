import asyncio
from typing import Any

import logfire
from dotenv import load_dotenv
from langchain_groq import ChatGroq

from app.models.resume import ResumeData
from app.services.content_extractor import ContentExtractor
from app.utils.file_utils import is_valid_resume_file

load_dotenv()

# Initialize the Langchain LLM Clients
base_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.0
)

vision_llm = ChatGroq(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    temperature=0.0
)

# Limits for LLM interactions to prevent very long-running requests
MAX_INPUT_CHARS = 20000
LLM_TIMEOUT_SECONDS = 60

# Semaphore to limit concurrent vision requests (prevents 429 errors)
vision_semaphore = asyncio.Semaphore(3)

# Initialize a logit-masker for strict output validation
structured_parser = base_llm.with_structured_output(
    ResumeData,
    method="json_mode",
    strict=True
)

async def extract_text_via_vision(images_base64: list[str]) -> str:
    """Use Groq Vision to extract text from images in parallel."""
    
    async def process_page(i: int, img_b64: str) -> str:
        async with vision_semaphore:
            logfire.info(f"Processing page/image {i+1} via Groq Vision")
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "Analyze this image. If it is a resume, extract all text and output ONLY the raw text found. If the image is NOT a resume (e.g., a photo, a menu, a book, a sign) or contains no text, output exactly: NOT_A_RESUME. Do not describe the image and do not add commentary."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_b64}"
                            }
                        }
                    ]
                }
            ]
            try:
                response = await vision_llm.ainvoke(messages)
                content = response.content.strip()
                
                if content == "NOT_A_RESUME":
                    logfire.warning(f"Vision model identified page {i+1} as NOT_A_RESUME")
                    return ""

                logfire.info(
                    f"Successfully extracted {len(content)} chars from page {i+1}", 
                    char_count=len(content)
                )
                return content
            except Exception as e:
                logfire.error(f"Vision LLM call failed for page {i+1}: {e}", error=str(e))
                return ""

    with logfire.span("extract_text_via_vision", page_count=len(images_base64)):
        # Run all pages in parallel
        tasks = [process_page(i, img_b64) for i, img_b64 in enumerate(images_base64)]
        results = await asyncio.gather(*tasks)
                
    return "\n\n".join(results)

async def structure_resume_with_llm(raw_text: str) -> ResumeData:
    """Use LLM to extract structured resume data from raw text."""
    from app.utils.prompt_loader import load_prompt

    with logfire.span("structure_resume_with_llm", text_length=len(raw_text)):
        system_prompt = load_prompt("resume_parser/system.md")
        user_prompt_template = load_prompt("resume_parser/user.md")

        # Guard against extremely large inputs from PDFs/OCR that slow the model.
        input_text = raw_text
        if len(raw_text) > MAX_INPUT_CHARS:
            logfire.warning(
                "Raw text too long; truncating before LLM call",
                original_length=len(raw_text),
                truncated_to=MAX_INPUT_CHARS,
            )
            input_text = raw_text[:MAX_INPUT_CHARS]

        user_prompt = user_prompt_template.format(raw_text=input_text)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            # Bound the LLM call so requests don't hang indefinitely.
            response = await asyncio.wait_for(
                structured_parser.ainvoke(messages), timeout=LLM_TIMEOUT_SECONDS
            )
            logfire.info("LLM successfully structured resume data")
            return response
        except asyncio.TimeoutError:
            logfire.error(
                "LLM call timed out",
                timeout_seconds=LLM_TIMEOUT_SECONDS,
                input_length=len(input_text),
                )
            raise ValueError(
                f"LLM call timed out after {LLM_TIMEOUT_SECONDS} seconds"
            )
        except Exception as e:
            logfire.error(f"LLM API call failed: {e}", error=str(e))
            raise ValueError(f"LLM API call failed: {e}") from e

async def parse_resume(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """
    Main entry point: file bytes → structured resume data.
    """
    with logfire.span("parse_resume", filename=filename, file_size=len(file_bytes)):
        # Step 1: Initial Validation
        is_valid, error = is_valid_resume_file(file_bytes, filename)
        if not is_valid:
            logfire.warning(f"File validation failed: {error}", filename=filename)
            raise ValueError(error)

        raw_text = ""
        filename_lower = filename.lower()

        # Step 2: Extract Text
        with logfire.span("text_extraction", filename=filename):
            if filename_lower.endswith(".pdf"):
                raw_text = await ContentExtractor.extract_text_from_pdf(file_bytes)
            elif filename_lower.endswith(".docx"):
                raw_text = await ContentExtractor.extract_text_from_docx(file_bytes)
            elif filename_lower.endswith(".txt"):
                try:
                    raw_text = file_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    # Fallback for other encodings
                    raw_text = file_bytes.decode("latin-1")
            elif any(filename_lower.endswith(ext) for ext in [".png", ".jpg", ".jpeg"]):
                img_b64 = ContentExtractor.prepare_image_for_ocr(file_bytes)
                raw_text = await extract_text_via_vision([img_b64])

        # Step 3: Quality Check and OCR Fallback for PDF
        if filename_lower.endswith(".pdf") and not ContentExtractor.validate_content_quality(raw_text):
            logfire.info(f"Text extraction insufficient for {filename}. Triggering OCR Fallback.")
            with logfire.span("ocr_fallback", filename=filename):
                images = ContentExtractor.render_pdf_to_images(file_bytes)
                if images:
                    raw_text = await extract_text_via_vision(images)

        # Step 4: Final Validation
        if not ContentExtractor.validate_content_quality(raw_text):
            snippet = raw_text[:500].replace("\n", " ")
            logfire.warning(
                f"Validation failed for {filename}: Document does not look like a resume.",
                snippet=snippet,
                full_extracted_text=raw_text
            )
            raise ValueError("The uploaded file does not appear to be a valid resume or is unreadable.")

        # Step 5: Structure with LLM
        resume_data_obj = await structure_resume_with_llm(raw_text)

        logfire.info("Resume successfully parsed and structured", filename=filename)
        return resume_data_obj.model_dump(), raw_text

