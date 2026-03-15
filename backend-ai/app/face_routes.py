import os
import logging
from dotenv import load_dotenv
from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from app.image_utils import read_and_detect_face_and_get_embedding

router = APIRouter()

logger = logging.getLogger("uvicorn.error")
load_dotenv()

API_KEY = os.getenv("API_KEY", "career-trust-ai-key")

def authorize_request(x_api_key: str | None):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

@router.post('/face-embedding')
async def face_embedding(
    file: UploadFile = File(...),
    x_api_key: str | None = Header(None),
):
    authorize_request(x_api_key)
    logger.info("face_embedding handler called")

    if os.environ.get("DEV_BYPASS_FACE", "0") in ("1", "true", "True"):
        return JSONResponse(content={"faceDetected": True, "dev_bypass": True})

    img_bytes = await file.read()
    _, emb = read_and_detect_face_and_get_embedding(img_bytes)

    if emb is None:
        return JSONResponse(
            content={"faceDetected": False, "error": "No valid single face detected"},
            status_code=200,
        )

    return JSONResponse(
        content={
            "faceDetected": True,
            "embedding": emb.tolist(),
        },
        status_code=200,
    )