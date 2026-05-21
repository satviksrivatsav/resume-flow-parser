import logging
import time
from typing import Annotated, Any, Optional

import logfire
from fastapi import APIRouter, File, HTTPException, UploadFile, Form
from pydantic import BaseModel

from app.models.field import Field, FieldMeta, FieldResponse
from app.models.tailor import TailorRequest
from app.services.field_processor import process_field_request
from app.services.resume_processor import parse_resume
from app.services.ats.ats_pipeline import process_ats_report
from app.services.content_extractor import ContentExtractor
from app.services.tailor_service import tailor_resume

router = APIRouter(prefix="/resume", tags=["Resume"])
logger = logging.getLogger(__name__)


@router.post("/tailor")
async def tailor_resume_endpoint(request: TailorRequest) -> dict[str, Any]:
    """
    Tailor resume content to a specific job description.
    """
    logfire.info("Received tailoring request")

    try:
        result = await tailor_resume(
            resume_data=request.resume_data,
            job_description=request.job_description,
            sections_to_tailor=request.sections_to_tailor
        )
        return {"success": True, "data": result}
    except ValueError as e:
        logfire.warning(f"Tailoring validation failed: {e}", error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logfire.error(f"Internal error during tailoring: {e}", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error during tailoring") from e


@router.post("/parse")
async def parse_resume_endpoint(file: Annotated[UploadFile, File(...)]) -> dict[str, Any]:
    """
    Parse a resume (PDF, DOCX, Image) and extract structured data.
    """
    if not file.filename:
        logfire.warning("Request received with no filename")
        raise HTTPException(status_code=400, detail="No filename provided")

    logfire.info(f"Received parse request for {file.filename}", filename=file.filename, content_type=file.content_type)

    try:
        file_bytes = await file.read()
        resume_data, _ = await parse_resume(file_bytes, file.filename)
        return {"success": True, "data": resume_data}
    except ValueError as e:
        logfire.warning(f"Resume parsing failed for {file.filename}: {e}", error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logfire.error(f"Internal error parsing resume {file.filename}: {e}", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error during parsing") from e


@router.post(path="/field")
async def field_action(request: Field) -> dict[str, Any]:
    """
    Process field level requests
    """

    # Mark the start time
    starting_time = time.time()

    # Validate the fields first
    if not request.action or request.action not in ["REWRITE", "GENERATE"]:
        raise HTTPException(
            status_code=400, detail="No Field action detected or Invalid action"
        )

    if not request.fieldName:
        raise HTTPException(
            status_code=400, detail="Invalid Resume Field or No field name detected"
        )

    if request.action == "REWRITE" and not request.originalText:
        raise HTTPException(
            status_code=400,
            detail="No existing text detected to perform REWRITE action",
        )

    # Process field request
    try:
        processed_field = process_field_request(**request.model_dump())
        time_taken = (time.time() - starting_time) * 1000
        response = FieldResponse(
            id="0",
            newText=processed_field,
            meta=FieldMeta(
                processingTimeMs=int(time_taken),
                action=request.action,
                fieldName=request.fieldName,
            ),
        )

        return {"success": True, "data": response}
    except Exception as e:
        logfire.error(f"Failed to process field {request.fieldName}: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


class AtsJsonRequest(BaseModel):
    resume_data: dict[str, Any]
    job_description: Optional[str] = None


@router.post("/ats")
async def ats_endpoint(
    file: Annotated[UploadFile, File(...)],
    job_description: Annotated[Optional[str], Form()] = None
) -> dict[str, Any]:
    """
    Parse a resume and generate a comprehensive ATS report.
    """
    if not file.filename:
        logfire.warning("Request received with no filename")
        raise HTTPException(status_code=400, detail="No filename provided")

    logfire.info(f"Received ATS request for {file.filename}")

    try:
        file_bytes = await file.read()
        
        # Parse structure and extract text in one go
        resume_data, raw_text = await parse_resume(file_bytes, file.filename)
        
        # Process ATS
        ats_report = await process_ats_report(
            filename=file.filename,
            file_bytes=file_bytes,
            raw_text=raw_text,
            parsed_data=resume_data,
            job_description=job_description
        )
        
        return {
            "success": True, 
            "data": {
                "parsed_resume": resume_data,
                "ats_report": ats_report.model_dump()
            }
        }
    except ValueError as e:
        logfire.warning(f"ATS processing failed for {file.filename}: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logfire.error(f"Internal error during ATS processing {file.filename}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during ATS processing") from e


@router.post("/ats/json")
async def ats_json_endpoint(request: AtsJsonRequest) -> dict[str, Any]:
    """
    Generate an ATS report from resume JSON data.
    """
    logfire.info("Received ATS request for JSON data")

    try:
        # Process ATS without file bytes and raw text
        ats_report = await process_ats_report(
            filename=None,
            file_bytes=None,
            raw_text=None,
            parsed_data=request.resume_data,
            job_description=request.job_description
        )
        
        return {
            "success": True, 
            "data": {
                "parsed_resume": request.resume_data,
                "ats_report": ats_report.model_dump()
            }
        }
    except Exception as e:
        logfire.error(f"Internal error during JSON ATS processing: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during ATS processing") from e


@router.post("/extract-text")
async def extract_text_endpoint(file: Annotated[UploadFile, File(...)]) -> dict[str, Any]:
    """
    Extract raw text from a file (PDF, DOCX, TXT).
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    try:
        file_bytes = await file.read()
        
        # Validate the uploaded file first
        from app.utils.file_utils import is_valid_resume_file
        is_valid, error = is_valid_resume_file(file_bytes, file.filename)
        if not is_valid:
            logfire.warning(f"File validation failed for extraction: {error}", filename=file.filename)
            raise HTTPException(status_code=400, detail=error)

        text = await ContentExtractor.extract_text(file_bytes, file.filename)
        return {"success": True, "data": text}
    except HTTPException:
        raise
    except Exception as e:
        logfire.error(f"Error extracting text from {file.filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to extract text from file") from e
