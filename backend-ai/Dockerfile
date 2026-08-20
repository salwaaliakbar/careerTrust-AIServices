FROM python:3.11-slim

# opencv/insightface/onnxruntime need these system libs to import at all
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download models at BUILD time so the first request doesn't pay for a
# slow (or, on a network-restricted host, failing) download.
RUN python -m spacy download en_core_web_lg
RUN python - <<'PY'
from sentence_transformers import SentenceTransformer
from transformers import DistilBertModel, DistilBertTokenizerFast
import insightface

SentenceTransformer("all-MiniLM-L6-v2")
DistilBertTokenizerFast.from_pretrained("distilbert-base-uncased")
DistilBertModel.from_pretrained("distilbert-base-uncased")
# Pulls the buffalo_l detection/recognition model pack into the image so
# face_recognition/image_utils.py's module-level FaceAnalysis().prepare()
# doesn't try to download it on first container start.
insightface.app.FaceAnalysis(providers=["CPUExecutionProvider"]).prepare(ctx_id=0, det_size=(640, 640))
PY

# app/model_output_v3 (fine-tuned sentiment DistilBERT checkpoint, ~254MB)
# is gitignored — too large for the git repo — so it lives in a Hugging
# Face Hub model repo instead and is pulled here at build time. Upload it
# once with scripts/upload_model_to_hf.py, then set the repo id below.
# Placed before `COPY app ./app` so code-only changes don't bust this layer
# and force a re-download every build.
ENV HF_MODEL_REPO="salwaaliakbar/careertrust-sentiment-distilbert"
RUN python - <<'PY'
import os
from huggingface_hub import snapshot_download

snapshot_download(repo_id=os.environ["HF_MODEL_REPO"], local_dir="app/model_output_v3")
PY

COPY app ./app

RUN test -f app/model_output_v3/best.pt || \
    (echo "Missing app/model_output_v3/best.pt after Hugging Face download — check HF_MODEL_REPO points at a repo containing best.pt." && exit 1)

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
