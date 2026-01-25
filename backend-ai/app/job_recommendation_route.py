from fastapi import APIRouter
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from typing import List, Dict

router = APIRouter()

# =============================
# Load model once (singleton)
# =============================
_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


# =============================
# Utility function
# =============================
def similarity(vec1, vec2):
    return float(cosine_similarity([vec1], [vec2])[0][0])


# =============================
# Recommendation API
# =============================
@router.post("/recommend")
def recommend(payload: Dict):

    model = get_model()

    user = payload.get("user", {})
    jobs = payload.get("jobs", [])

    # =============================
    # USER TEXT PARTS
    # =============================
    user_skills_text = ", ".join(user.get("skills", []))
    user_summary_text = user.get("summary", "")
    user_title_text = user.get("headline", "")
    user_experience = str(user.get("totalExperience", ""))

    # =============================
    # USER EMBEDDINGS
    # =============================
    user_skills_vec = model.encode(user_skills_text)
    user_summary_vec = model.encode(user_summary_text)
    user_title_vec = model.encode(user_title_text)
    user_exp_vec = model.encode(user_experience)

    recommendations = []

    # =============================
    # JOB LOOP
    # =============================
    for job in jobs:

        job_skills_text = ", ".join(job.get("skills", []))
        job_desc_text = job.get("description", "")
        job_title_text = job.get("title", "")
        job_experience = str(job.get("experience", ""))

        # Job embeddings
        job_skills_vec = model.encode(job_skills_text)
        job_desc_vec = model.encode(job_desc_text)
        job_title_vec = model.encode(job_title_text)
        job_exp_vec = model.encode(job_experience)

        # =============================
        # Similarities
        # =============================
        skills_sim = similarity(user_skills_vec, job_skills_vec)
        summary_sim = similarity(user_summary_vec, job_desc_vec)
        title_sim = similarity(user_title_vec, job_title_vec)
        exp_sim = similarity(user_exp_vec, job_exp_vec)

        # =============================
        # Weighted final score
        # =============================
        final_score = (
            0.50 * skills_sim +
            0.25 * summary_sim +
            0.15 * title_sim +
            0.10 * exp_sim
        )

        recommendations.append({
            "job_id": job.get("id"),
            "score": round(final_score, 4),

            # Optional explainability
            "breakdown": {
                "skills": round(skills_sim, 3),
                "summary": round(summary_sim, 3),
                "title": round(title_sim, 3),
                "experience": round(exp_sim, 3),
            }
        })

    # Sort best match first
    recommendations.sort(key=lambda x: x["score"], reverse=True)

    return {
        "recommendations": recommendations
    }
