from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from app.image_utils import read_and_detect_face_and_get_embedding
from app.face_model import get_all_embeddings, add_embedding
import numpy as np
import os

app = FastAPI()
THRESHOLD = 0.7  # cosine similarity threshold

@app.post('/face-recognition')
async def face_recognition(file: UploadFile = File(...), user_id: str = Form(None), save_if_new: str = Form("0")):
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
