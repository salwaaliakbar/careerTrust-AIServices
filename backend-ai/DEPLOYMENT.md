# Deploying backend-ai to Render

## Render setup
1. New → Web Service → pick this repo → **Environment: Docker** (Render will build the `Dockerfile` at the repo's `backend-ai/` root; set that as the "Root Directory" if the repo contains more than this service).
2. Environment variables (Render dashboard → Environment):
   - `API_KEY` — long random string; the Node backend must send this same value as `AI_API_KEY`/`X-API-Key`.
   - `ALLOWED_ORIGINS` — your Vercel frontend URL, e.g. `https://your-app.vercel.app`. Add the Render backend URL too only if it calls this service directly from a browser context (server-to-server calls don't need CORS).
   - `DEV_BYPASS_FACE` — leave unset or `false`.
3. Render sets `$PORT` automatically; the Dockerfile's `CMD` already reads it.

## Free-tier RAM warning
This service loads, at minimum: spaCy `en_core_web_lg` (~560MB on disk), a DistilBERT encoder, a MiniLM sentence-transformer, insightface's `buffalo_l` pack, and PyTorch itself. Loaded together in one process this is comfortably over Render's free instance limit (512MB RAM) — expect it to be OOM-killed on first request even though the Docker build succeeds.

Two ways forward:
- **Try it anyway** — Render's free tier costs nothing to attempt; if it OOM-kills, you'll see it immediately in the logs.
- **Move this one service to a Hugging Face Space** (Docker SDK, free tier gives more RAM than Render's free instance) if it does OOM. The same `Dockerfile` should work there with minimal changes — HF Spaces expects the app to listen on port 7860 by default (still controlled by the `PORT` env var here, so just set `PORT=7860` in the Space's settings).

## Before building the image
`app/model_output_v3/` (the fine-tuned sentiment DistilBERT, ~254MB) is gitignored — too large for GitHub — and is instead hosted on Hugging Face Hub and pulled at Docker build time.

One-time setup:
1. `pip install huggingface_hub && huggingface-cli login` (paste a token from https://huggingface.co/settings/tokens).
2. `python scripts/upload_model_to_hf.py <your-username>/careertrust-sentiment-distilbert` — creates the repo (public, free, no bandwidth cap) and uploads `best.pt` + tokenizer files.
3. In `Dockerfile`, set `ENV HF_MODEL_REPO="<your-username>/careertrust-sentiment-distilbert"` to match.

After that, every `docker build` (including Render's) downloads the checkpoint from HF Hub automatically — no manual copy step, and nothing to configure on Render itself for this part.
