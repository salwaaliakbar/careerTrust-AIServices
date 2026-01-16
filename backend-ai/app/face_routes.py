from fastapi import APIRouter, File, UploadFile, Form
from fastapi.responses import JSONResponse
from app.image_utils import read_and_detect_face_and_get_embedding
from app.face_model import get_all_embeddings, add_embedding
import numpy as np
import os
from app.face_model import get_embedding_by_user
import logging

router = APIRouter()

logger = logging.getLogger("uvicorn.error")

THRESHOLD = 0.7  # cosine similarity threshold

@router.post('/face-recognition')
async def face_recognition(file: UploadFile = File(...), user_id: str = Form(None), save_if_new: str = Form("0")):
    logger.info(f"face_recognition handler called; user_id={user_id} save_if_new={save_if_new}")

    if os.environ.get("DEV_BYPASS_FACE", "0") in ("1", "true", "True"):
        return JSONResponse(content={"match": False, "dev_bypass": True})

    img_bytes = await file.read()
    face_img, emb = read_and_detect_face_and_get_embedding(img_bytes)

    if emb is None:
        return JSONResponse(content={"match": False, "error": "No valid single face detected"}, status_code=200)

    matches = []
    try:
        for db_user_id, db_emb in get_all_embeddings():
            sim = np.dot(emb, db_emb) / (np.linalg.norm(emb) * np.linalg.norm(db_emb))
            if sim > THRESHOLD:
                matches.append({'user_id': db_user_id, 'confidence': float(sim)})
    except Exception as e:
        return JSONResponse(content={"match": False, "error": "DB error", "details": str(e)}, status_code=500)

    if matches:
        best_match = max(matches, key=lambda x: x['confidence'])
        return JSONResponse(content={"match": True, **best_match})

    if save_if_new.lower() in ("1", "true", "yes") and user_id:
        try:
            add_embedding(user_id, emb)
            return JSONResponse(content={"match": False, "saved": True})
        except Exception as e:
            return JSONResponse(content={"match": False, "saved": False, "error": "DB save failed", "details": str(e)}, status_code=500)

    return JSONResponse(content={"match": False})

@router.post('/face-verify')
async def face_verify(file: UploadFile = File(...), user_id: str = Form(...)):
    """
    Verify uploaded image matches the stored embedding for the given user_id (email).
    Returns JSON: { match: bool, similarity?: float, error?: string }
    """
    logger.info(f"face_verify handler called; user_id={user_id}")

    if os.environ.get("DEV_BYPASS_FACE", "0") in ("1", "true", "True"):
        return JSONResponse(content={"match": False, "dev_bypass": True})

    if not user_id:
        return JSONResponse(content={"match": False, "error": "user_id (email) is required"}, status_code=400)

    img_bytes = await file.read()
    face_img, emb = read_and_detect_face_and_get_embedding(img_bytes)

    if emb is None:
        return JSONResponse(content={"match": False, "error": "No valid single face detected"}, status_code=200)

    try:
        db_emb = get_embedding_by_user(user_id)  # returns numpy array or None
    except Exception as e:
        return JSONResponse(content={"match": False, "error": "DB error", "details": str(e)}, status_code=500)

    if db_emb is None:
        return JSONResponse(content={"match": False, "error": "No stored embedding for this user_id"}, status_code=404)

    # compute cosine similarity
    sim = float(np.dot(emb, db_emb) / (np.linalg.norm(emb) * np.linalg.norm(db_emb)))
    if sim >= THRESHOLD:
        return JSONResponse(content={"match": True, "similarity": sim})
    else:
        return JSONResponse(content={"match": False, "similarity": sim, "error": "Face embedding does not match"})