from threading import Lock

import insightface
import numpy as np
import cv2

# InsightFace's detection+recognition pack is loaded on first use instead of
# at import time, so a process that never gets a face-recognition request
# never pays the RAM cost for it.
_app = None
_app_lock = Lock()


def _get_app():
    global _app
    if _app is None:
        with _app_lock:
            if _app is None:
                loaded = insightface.app.FaceAnalysis(
                name="buffalo_s",
                root="/srv/.insightface",
                providers=["CPUExecutionProvider"],
                )
                loaded.prepare(ctx_id=0, det_size=(320, 320))
                _app = loaded
    return _app


def read_and_detect_face_and_get_embedding(image_bytes):
    npimg = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    if img is None:
        return None, None

    faces = _get_app().get(img)

    # Ensure exactly one face detected
    if len(faces) != 1:
        return None, None

    face = faces[0]
    # Normalized embedding vector
    embedding = face.embedding / np.linalg.norm(face.embedding)

    # Crop detected face (optional, if you want to process or save face image)
    x1, y1, x2, y2 = map(int, face.bbox.flatten())
    cropped_face = img[y1:y2, x1:x2]

    return cropped_face, embedding
