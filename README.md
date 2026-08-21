# CareerTrust — AI Services

FastAPI microservice providing the machine learning features behind [CareerTrust](https://career-trust-frontend.vercel.app): resume parsing, face-verification embeddings, review sentiment/reputation scoring, and AI-assisted job recommendations.

**Demo video:** [Watch on Google Drive](https://drive.google.com/file/d/1OHbpxpA-Cr3Ty2lUqKvng1T5XsgXxJTV/view?usp=sharing)

> **Deployment status:** This service is **not currently serving live traffic** in the hosted deployment. The combined footprint of spaCy, a fine-tuned DistilBERT sentiment model, a MiniLM sentence-transformer, and InsightFace's face-recognition models exceeds what free-tier hosting (512MB RAM on Render, or Hugging Face Spaces' concurrency quota) can reliably run. Every feature below is fully implemented and demonstrated in the video above; see `backend-ai/DEPLOYMENT.md` for the deployment details and constraints.

## Overview

This repository contains the Python/FastAPI AI service used by CareerTrust. It provides:

- **Job recommendation and matching** — hybrid semantic (sentence-transformers) + rule-based scoring across skills, job title, experience, and summary
- **Face detection and embedding extraction** — identity verification during onboarding (InsightFace)
- **Resume parsing** — structured extraction from PDF/DOCX resumes (spaCy NER + pattern matching)
- **Review sentiment analysis** — a fine-tuned multi-head DistilBERT regressor scoring reviews across five dimensions (overall rating, work-life balance, company culture, career opportunities, salary/benefits), feeding the platform's company reputation scores

Primary service directory: `backend-ai/`

## Tech Stack

- **Framework:** FastAPI + Uvicorn
- **ML/NLP:** PyTorch, Transformers (DistilBERT), Sentence-Transformers (MiniLM), spaCy
- **Computer vision:** InsightFace, OpenCV
- **Model hosting:** Hugging Face Hub (the fine-tuned sentiment checkpoint is downloaded on first use rather than committed to git — see `backend-ai/DEPLOYMENT.md`)

## Repository Structure

```text
careerTrust-AIServices/
└─ backend-ai/
   ├─ app/
   │  ├─ face_recognition/        # Face embedding routes and utilities
   │  ├─ resume/                  # Resume parsing routes and parser
   │  ├─ job_recommendation/      # Job recommendation engine modules
   │  ├─ sentiment_analysis/      # Review sentiment inference routes
   │  └─ main.py                  # FastAPI app entrypoint
   ├─ model_output_v3/            # Fine-tuned sentiment model artifacts (gitignored; pulled from HF Hub)
   ├─ requirements.txt            # Python dependencies
   ├─ Dockerfile                  # Container build (used for Hugging Face Spaces)
   ├─ DEPLOYMENT.md               # Deployment steps, env vars, and hosting constraints
   ├─ MATCHING_ARCHITECTURE.md    # Job-matching design and scoring rationale
   ├─ test_matching_examples.py   # Matching behavior examples
   └─ test_model_diagnostics.py   # Model diagnostics script
```

## Quick Start (local development)

```powershell
cd backend-ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Copy `backend-ai/app/.env.example` to `backend-ai/app/.env` and fill in `API_KEY`, `ALLOWED_ORIGINS`, and `HF_MODEL_REPO` before starting the server — the sentiment endpoint downloads its model from Hugging Face Hub on first request.

Service will be available at `http://localhost:8000`.

## Running Diagnostics and Tests

From `backend-ai/`:

```powershell
python test_matching_examples.py
python test_model_diagnostics.py
```

## Matching System

The recommendation engine uses a production-oriented hybrid approach:

- **Skills** — set coverage + semantic similarity + bonus logic
- **Job title** — semantic similarity + hierarchy awareness
- **Experience** — numeric rule-based scoring
- **Summary** — semantic relevance scoring

For detailed design and scoring rationale, see `backend-ai/MATCHING_ARCHITECTURE.md`.

## Notes

- This service extracts and returns face embeddings; storage and duplicate checks are handled by the main [backend](https://github.com/salwaaliakbar/careerTrust-backend).
- All heavy models (spaCy, InsightFace, DistilBERT, MiniLM) are lazy-loaded on first use rather than at process startup, so a fresh instance boots without paying for every model up front.
- Keep `.venv/` and `model_output_v3/` out of version control — see `backend-ai/DEPLOYMENT.md` for how the sentiment checkpoint is hosted and pulled instead.

## Troubleshooting

If `insightface` fails to install on Windows:

1. Install Visual C++ Build Tools (Desktop development with C++).
2. Reopen PowerShell.
3. Retry: `pip install -r requirements.txt`.

## Related Repositories

- **Frontend** — https://github.com/salwaaliakbar/CareerTrust-frontend
- **Backend** — https://github.com/salwaaliakbar/careerTrust-backend

## License

Private/internal project for CareerTrust.
