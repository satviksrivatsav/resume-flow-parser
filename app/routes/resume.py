from fastapi import APIRouter, File, UploadFile, HTTPException
from app.services.resume_parser import parse_resume_pdf
import logging

router = APIRouter(prefix="/resume", tags=["Resume"])
logger = logging.getLogger(__name__)


@router.post("/parse")
async def parse_resume(file: UploadFile = File(...)):
    """
    Parse a PDF resume and extract structured data.
    
    Returns ResumeData matching the frontend type structure.
    """
    # Validate file type
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Check file size (10MB limit)
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    
    try:
        # Read file bytes
        pdf_bytes = await file.read()
        
        # Parse resume
        resume_data = await parse_resume_pdf(pdf_bytes)
        
        return {
            "success": True,
            "data": resume_data
        }
    except ValueError as e:
        logger.warning(f"Resume parsing failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to parse resume")
        raise HTTPException(status_code=500, detail=str(e))
