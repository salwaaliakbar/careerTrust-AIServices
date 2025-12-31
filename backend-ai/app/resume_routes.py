import os
from dotenv import load_dotenv
from fastapi import APIRouter, File, UploadFile, Header, HTTPException
from fastapi.responses import JSONResponse
from app.pyresume_parser import parse_resume_file

router = APIRouter()

# Load environment variables from a .env file if present
load_dotenv()

# Read API key from environment, fall back to a default for local testing
# Set `API_KEY` in your .env or environment to override.
API_KEY = os.getenv("API_KEY", "career-trust-ai-key")

@router.post('/parse-resume')
async def parse_resume(file: UploadFile = File(...), x_api_key: str | None = Header(None), fullName: str | None = None, email: str | None = None):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    contents = await file.read()
    filename = file.filename or "resume"

    try:
        # Parse using pyresume; pass filename so parser can detect PDFs/DOCX
        parsed = parse_resume_file(contents, fullName, email, filename=filename)
        return {"parsed": parsed, "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parsing error: {str(e)}")
