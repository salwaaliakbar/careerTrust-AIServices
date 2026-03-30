import os
from dotenv import load_dotenv
from fastapi import APIRouter, File, UploadFile, Header, HTTPException, Form
from fastapi.responses import JSONResponse
from app.resume.parser import parse_resume_file
import traceback

router = APIRouter()

# Load environment variables from a .env file if present
load_dotenv()

# Read API key from environment, fall back to a default for local testing
# Set `API_KEY` in your .env or environment to override.
API_KEY = os.getenv("API_KEY", "career-trust-ai-key")

@router.post('/parse-resume')
async def parse_resume(file: UploadFile = File(...), 
    x_api_key: str | None = Header(None), 
    fullName: str = Form(""), 
    email: str = Form("")
    ):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    contents = await file.read()
    filename = file.filename or "resume"

    try:
        # Parse using pyresume; pass filename so parser can detect PDFs/DOCX
        parsed = parse_resume_file(contents, filename=filename)

        print(f"Parsed resume for: {parsed.get('name')}")
        print("full name:", fullName)

        print("email:", email)
        print("parsed email:", parsed.get("email"))
        mismatches = {
        "name": parsed.get("name") != fullName,
        "email": parsed.get("email") != email,
        }
        
        return {
        "parsed": parsed,
        "mismatches": mismatches,
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Parsing error: {str(e)}")
