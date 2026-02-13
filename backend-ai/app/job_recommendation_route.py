"""
Production-Grade Job Recommendation Engine

Architectural Principles:
=========================
1. Hybrid Matching: Combines rule-based constraints with semantic similarity
2. Component Separation: Each matching dimension (skills, title, experience) 
   uses appropriate strategy
3. Explainability: Every score is fully decomposed and traceable
4. No False Penalization: Extra qualifications boost or maintain scores

System Design:
==============
┌─────────────────┐
│  User Profile   │
│  Job Posting    │
└────────┬────────┘
         │
    ┌────▼─────────────────────────────────┐
    │   MATCHING PIPELINE                  │
    │                                      │
    │  ┌──────────────────────────────┐   │
    │  │ 1. Skills Matcher            │   │
    │  │    - Set coverage (required) │   │
    │  │    - Semantic similarity     │   │
    │  │    - Bonus for extra skills  │   │
    │  └──────────────────────────────┘   │
    │                                      │
    │  ┌──────────────────────────────┐   │
    │  │ 2. Title Matcher             │   │
    │  │    - Semantic similarity     │   │
    │  │    - Hierarchy awareness     │   │
    │  │    - Specialization boost    │   │
    │  └──────────────────────────────┘   │
    │                                      │
    │  ┌──────────────────────────────┐   │
    │  │ 3. Experience Matcher        │   │
    │  │    - Numeric rule-based      │   │
    │  │    - Min/max constraints     │   │
    │  │    - No over-qualification   │   │
    │  │      penalization            │   │
    │  └──────────────────────────────┘   │
    │                                      │
    │  ┌──────────────────────────────┐   │
    │  │ 4. Summary Matcher           │   │
    │  │    - Pure semantic (correct) │   │
    │  └──────────────────────────────┘   │
    │                                      │
    │  ┌──────────────────────────────┐   │
    │  │ 5. Score Aggregator          │   │
    │  │    - Weighted combination    │   │
    │  │    - Confidence scoring      │   │
    │  └──────────────────────────────┘   │
    └──────────────────┬───────────────────┘
                       │
              ┌────────▼────────┐
              │  Ranked Results │
              │  + Explainability│
              └─────────────────┘

Scoring Formula (0-100 scale):
===============================
Final Score = 
    0.45 × Skills_Score +
    0.25 × Summary_Score + 
    0.20 × Title_Score +
    0.10 × Experience_Score

Where:
- Skills_Score = 0.6 × Coverage + 0.3 × Semantic + 0.1 × Bonus
- Title_Score = 0.7 × Semantic + 0.3 × Hierarchy
- Experience_Score = Rule-based (numeric comparison)
- Summary_Score = Cosine similarity (semantic)

"""

from fastapi import APIRouter
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Set, Tuple, Optional
import numpy as np
import re

router = APIRouter()

# =============================
# Model Singleton
# =============================
_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


# =============================
# Utility Functions
# =============================
def cosine_sim(vec1, vec2) -> float:
    """Compute cosine similarity between two vectors"""
    return float(cosine_similarity([vec1], [vec2])[0][0])


def normalize_skill(skill: str) -> str:
    """Normalize skill for comparison (lowercase, trim, remove special chars)"""
    return re.sub(r'[^\w\s]', '', skill.lower().strip())


def parse_experience(exp_text: str) -> Optional[float]:
    """
    Extract numeric experience from text
    Examples: "3 years", "2-4 years", "5+ years" -> 3.0, 3.0, 5.0
    """
    if not exp_text:
        return None
    
    # Try to extract numbers
    numbers = re.findall(r'\d+\.?\d*', str(exp_text))
    if not numbers:
        return None
    
    # If range (e.g., "2-4"), take minimum
    return float(numbers[0])


# =============================
# COMPONENT 1: Skills Matcher
# =============================
class SkillsMatcher:
    """
    Hybrid skills matching strategy:
    
    Issues with pure embedding approach:
    - Candidate with [Python, Java, C++, React, Django] 
      vs Job requiring [Python, Django]
    - Embedding distance increases due to extra skills
    - Pure cosine similarity penalizes qualified candidates
    
    Solution:
    1. Set-based coverage: Required skills must be present (hard constraint)
    2. Semantic matching: Handle synonyms (e.g., "JS" ≈ "JavaScript")
    3. Bonus scoring: Extra relevant skills are positive signals
    """
    
    def __init__(self, model):
        self.model = model
        
    def match(
        self, 
        candidate_skills: List[str], 
        job_required_skills: List[str],
        job_optional_skills: List[str] = None
    ) -> Dict:
        """
        Returns:
        {
            "score": 0-100,
            "coverage": 0-100,      # % of required skills covered
            "semantic": 0-100,      # semantic similarity
            "bonus": 0-100,         # extra skills bonus
            "missing_skills": [...],
            "extra_skills": [...]
        }
        """
        if not job_required_skills:
            return {
                "score": 100.0,
                "coverage": 100.0,
                "semantic": 100.0,
                "bonus": 0.0,
                "missing_skills": [],
                "extra_skills": candidate_skills
            }
        
        job_optional_skills = job_optional_skills or []
        
        # Normalize skills
        candidate_norm = {normalize_skill(s): s for s in candidate_skills}
        required_norm = {normalize_skill(s): s for s in job_required_skills}
        optional_norm = {normalize_skill(s): s for s in job_optional_skills}
        
        # ===== 1. COVERAGE SCORE (Set-based) =====
        # Direct string matching
        direct_matches = set(candidate_norm.keys()) & set(required_norm.keys())
        missing_required = set(required_norm.keys()) - set(candidate_norm.keys())
        
        # Semantic matching for missing skills (handle synonyms)
        semantically_matched = set()
        if missing_required and candidate_skills:
            for missing in list(missing_required):
                missing_vec = self.model.encode(required_norm[missing])
                
                for cand_norm, cand_orig in candidate_norm.items():
                    if cand_norm in direct_matches or cand_norm in semantically_matched:
                        continue
                    
                    cand_vec = self.model.encode(cand_orig)
                    sim = cosine_sim(missing_vec, cand_vec)
                    
                    # High threshold for synonym matching (e.g., "JS" vs "JavaScript")
                    if sim > 0.85:
                        semantically_matched.add(missing)
                        break
        
        total_matched = len(direct_matches) + len(semantically_matched)
        coverage_score = (total_matched / len(required_norm)) * 100 if required_norm else 100.0
        
        # ===== 2. SEMANTIC SIMILARITY SCORE =====
        # Use embeddings for overall skill alignment
        candidate_text = ", ".join(candidate_skills) if candidate_skills else "none"
        required_text = ", ".join(job_required_skills)
        
        candidate_vec = self.model.encode(candidate_text)
        required_vec = self.model.encode(required_text)
        
        semantic_score = cosine_sim(candidate_vec, required_vec) * 100
        
        # ===== 3. BONUS SCORE (Extra Skills) =====
        # Extra skills that match optional or are generally relevant
        extra_skills = set(candidate_norm.keys()) - set(required_norm.keys())
        
        bonus_score = 0.0
        if extra_skills:
            # Match against optional skills
            optional_matches = extra_skills & set(optional_norm.keys())
            bonus_score = min((len(optional_matches) / max(len(optional_norm), 1)) * 100, 50.0)
            
            # If no optional skills defined, generic bonus for having extra skills
            if not job_optional_skills:
                bonus_score = min(len(extra_skills) * 2, 20.0)
        
        # ===== FINAL SKILLS SCORE =====
        # Coverage is most important, semantic second, bonus is extra credit
        final_score = (
            0.60 * coverage_score +
            0.30 * semantic_score +
            0.10 * bonus_score
        )
        
        return {
            "score": round(final_score, 2),
            "coverage": round(coverage_score, 2),
            "semantic": round(semantic_score, 2),
            "bonus": round(bonus_score, 2),
            "missing_skills": [required_norm[s] for s in (missing_required - semantically_matched)],
            "extra_skills": [candidate_norm[s] for s in extra_skills]
        }


# =============================
# COMPONENT 2: Title Matcher
# =============================
class TitleMatcher:
    """
    Job title matching with hierarchy awareness
    
    Problem:
    - "Full Stack AI Engineer" vs "Full Stack Engineer"
    - Pure embedding similarity decreases
    - But "AI Engineer" is a specialization, not a mismatch
    
    Solution:
    1. Semantic similarity as baseline
    2. Hierarchy detection: if candidate title contains job title + extras
    3. Specialization boost: domain-specific keywords increase score
    """
    
    def __init__(self, model):
        self.model = model
        
        # Common title hierarchies and synonyms
        self.seniority_levels = ['intern', 'junior', 'mid', 'senior', 'lead', 'principal', 'staff', 'architect']
        self.specializations = ['ai', 'ml', 'data', 'cloud', 'devops', 'security', 'mobile', 'frontend', 'backend', 'fullstack', 'full stack']
        
    def match(self, candidate_title: str, job_title: str) -> Dict:
        """
        Returns:
        {
            "score": 0-100,
            "semantic": 0-100,
            "hierarchy_boost": 0-50,
            "is_overqualified": bool,
            "is_underqualified": bool
        }
        """
        if not job_title or not candidate_title:
            return {
                "score": 0.0,
                "semantic": 0.0,
                "hierarchy_boost": 0.0,
                "is_overqualified": False,
                "is_underqualified": False
            }
        
        # ===== 1. SEMANTIC SIMILARITY =====
        cand_vec = self.model.encode(candidate_title)
        job_vec = self.model.encode(job_title)
        semantic_score = cosine_sim(cand_vec, job_vec) * 100
        
        # ===== 2. HIERARCHY ANALYSIS =====
        cand_lower = candidate_title.lower()
        job_lower = job_title.lower()
        
        hierarchy_boost = 0.0
        is_overqualified = False
        is_underqualified = False
        
        # Extract seniority levels
        cand_seniority = [s for s in self.seniority_levels if s in cand_lower]
        job_seniority = [s for s in self.seniority_levels if s in job_lower]
        
        # Check if candidate title contains job title (specialization case)
        # e.g., "Full Stack AI Engineer" contains "Full Stack Engineer"
        job_core_words = set(job_lower.split())
        cand_core_words = set(cand_lower.split())
        
        overlap = job_core_words & cand_core_words
        overlap_ratio = len(overlap) / len(job_core_words) if job_core_words else 0
        
        # Specialization: candidate has all job words + extras
        if overlap_ratio > 0.7:
            extra_words = cand_core_words - job_core_words
            # Check if extras are specializations (positive signal)
            if any(spec in ' '.join(extra_words) for spec in self.specializations):
                hierarchy_boost = 15.0
        
        # Seniority comparison
        if cand_seniority and job_seniority:
            cand_level = self.seniority_levels.index(cand_seniority[0])
            job_level = self.seniority_levels.index(job_seniority[0])
            
            if cand_level > job_level:
                is_overqualified = True
                hierarchy_boost = max(hierarchy_boost, 10.0)  # Slight boost
            elif cand_level < job_level:
                is_underqualified = True
                hierarchy_boost = -20.0  # Penalty for under-qualification
        
        # ===== FINAL TITLE SCORE =====
        final_score = min(max(
            0.70 * semantic_score + 
            0.30 * hierarchy_boost,
            0
        ), 100)
        
        return {
            "score": round(final_score, 2),
            "semantic": round(semantic_score, 2),
            "hierarchy_boost": round(hierarchy_boost, 2),
            "is_overqualified": is_overqualified,
            "is_underqualified": is_underqualified
        }


# =============================
# COMPONENT 3: Experience Matcher
# =============================
class ExperienceMatcher:
    """
    Numeric experience matching (NOT embedding-based)
    
    Why embeddings are wrong here:
    - Job requires "2 years", candidate has "5 years"
    - Embedding similarity of "2" vs "5" is meaningless
    - This is a numerical constraint satisfaction problem
    
    Solution:
    - Parse numeric values
    - Apply rule-based logic:
      * Below minimum: low score
      * Within range: high score
      * Above maximum (if specified): maintain high score
      * Over-qualified: NO penalty (wrong assumption in many systems)
    """
    
    def match(
        self, 
        candidate_years: float, 
        job_min_years: float = None,
        job_max_years: float = None
    ) -> Dict:
        """
        Returns:
        {
            "score": 0-100,
            "meets_minimum": bool,
            "within_range": bool,
            "years_difference": float
        }
        """
        if job_min_years is None:
            return {
                "score": 100.0,
                "meets_minimum": True,
                "within_range": True,
                "years_difference": 0.0
            }
        
        # ===== RULE-BASED SCORING =====
        meets_minimum = candidate_years >= job_min_years
        
        years_diff = candidate_years - job_min_years
        
        # Score calculation
        if candidate_years < job_min_years:
            # Under-qualified: proportional penalty
            gap = job_min_years - candidate_years
            score = max(0, 100 - (gap * 20))  # -20 points per year short
        
        elif job_max_years and candidate_years > job_max_years:
            # Over maximum but NO penalty - they're still qualified
            # Slight reduction only if significantly over (e.g., 10+ years for entry role)
            excess = candidate_years - job_max_years
            score = max(85, 100 - (excess * 2))
        
        else:
            # Within range or above minimum with no max specified
            score = 100.0
        
        within_range = (
            candidate_years >= job_min_years and 
            (job_max_years is None or candidate_years <= job_max_years + 3)
        )
        
        return {
            "score": round(score, 2),
            "meets_minimum": meets_minimum,
            "within_range": within_range,
            "years_difference": round(years_diff, 2)
        }


# =============================
# COMPONENT 4: Summary Matcher
# =============================
class SummaryMatcher:
    """
    Professional summary vs job description matching
    
    This is the ONE place where pure semantic similarity is correct:
    - Free-form text describing experience, goals, background
    - Semantic alignment with job description is meaningful
    - Embeddings capture intent and domain relevance
    """
    
    def __init__(self, model):
        self.model = model
        
    def match(self, candidate_summary: str, job_description: str) -> Dict:
        """
        Returns:
        {
            "score": 0-100,
            "semantic": 0-100
        }
        """
        if not job_description or not candidate_summary:
            return {
                "score": 50.0,  # Neutral score if missing
                "semantic": 50.0
            }
        
        cand_vec = self.model.encode(candidate_summary)
        job_vec = self.model.encode(job_description)
        
        semantic_score = cosine_sim(cand_vec, job_vec) * 100
        
        return {
            "score": round(semantic_score, 2),
            "semantic": round(semantic_score, 2)
        }


# =============================
# COMPONENT 5: Score Aggregator
# =============================
class ScoreAggregator:
    """
    Combines individual match scores with domain-appropriate weights
    
    Weighting rationale:
    - Skills (45%): Most important - can they do the job?
    - Summary (25%): Context and experience relevance
    - Title (20%): Role alignment and career fit
    - Experience (10%): Threshold check, less discriminative if minimum met
    """
    
    WEIGHTS = {
        "skills": 0.45,
        "summary": 0.25,
        "title": 0.20,
        "experience": 0.10
    }
    
    @classmethod
    def aggregate(
        cls,
        skills_result: Dict,
        title_result: Dict,
        experience_result: Dict,
        summary_result: Dict
    ) -> Dict:
        """
        Returns:
        {
            "final_score": 0-100,
            "confidence": 0-100,
            "breakdown": {...},
            "flags": [...]
        }
        """
        # Calculate weighted final score
        final_score = (
            cls.WEIGHTS["skills"] * skills_result["score"] +
            cls.WEIGHTS["summary"] * summary_result["score"] +
            cls.WEIGHTS["title"] * title_result["score"] +
            cls.WEIGHTS["experience"] * experience_result["score"]
        )
        
        # Confidence score (how reliable is this match?)
        confidence_factors = []
        
        # High skills coverage increases confidence
        if skills_result["coverage"] > 80:
            confidence_factors.append(20)
        elif skills_result["coverage"] > 60:
            confidence_factors.append(10)
        
        # Meeting experience threshold increases confidence
        if experience_result["meets_minimum"]:
            confidence_factors.append(15)
        
        # Strong semantic alignment increases confidence
        if summary_result["semantic"] > 70:
            confidence_factors.append(15)
        
        confidence = min(50 + sum(confidence_factors), 100)
        
        # Flags for HR review
        flags = []
        if skills_result["missing_skills"]:
            flags.append(f"Missing {len(skills_result['missing_skills'])} required skills")
        if not experience_result["meets_minimum"]:
            flags.append("Below minimum experience requirement")
        if title_result.get("is_underqualified"):
            flags.append("Title suggests under-qualification")
        if title_result.get("is_overqualified"):
            flags.append("Potentially over-qualified (review for flight risk)")
        
        return {
            "final_score": round(final_score, 2),
            "confidence": round(confidence, 2),
            "breakdown": {
                "skills": skills_result,
                "title": title_result,
                "experience": experience_result,
                "summary": summary_result
            },
            "flags": flags
        }


# =============================
# API ENDPOINT
# =============================
@router.post("/recommend")
def recommend(payload: Dict):
    """
    Job recommendation endpoint with production-grade matching logic
    
    Expected payload:
    {
        "user": {
            "skills": ["Python", "Django", "React"],
            "requiredSkills": ["Python", "Django"],  # Optional: specify which are required
            "optionalSkills": ["React"],             # Optional
            "headline": "Senior Full Stack Engineer",
            "summary": "10 years of experience building...",
            "totalExperience": 10.0  # numeric value preferred, or "10 years"
        },
        "jobs": [
            {
                "id": "job_123",
                "title": "Full Stack Engineer",
                "description": "We are looking for...",
                "skills": ["Python", "Django"],
                "requiredSkills": ["Python"],        # Optional
                "optionalSkills": ["Django", "React"], # Optional
                "minExperience": 3.0,                # numeric
                "maxExperience": 8.0                 # optional
            },
            ...
        ]
    }
    """
    
    model = get_model()
    
    # Initialize matchers
    skills_matcher = SkillsMatcher(model)
    title_matcher = TitleMatcher(model)
    experience_matcher = ExperienceMatcher()
    summary_matcher = SummaryMatcher(model)
    
    user = payload.get("user", {})
    jobs = payload.get("jobs", [])
    
    # Parse user profile
    user_skills = user.get("skills", [])
    user_title = user.get("headline", "")
    user_summary = user.get("summary", "")
    user_experience = user.get("totalExperience", 0)
    
    # Parse experience if it's a string
    if isinstance(user_experience, str):
        user_experience = parse_experience(user_experience) or 0
    
    recommendations = []
    
    # =============================
    # Match each job
    # =============================
    for job in jobs:
        job_id = job.get("id", "unknown")
        job_title = job.get("title", "")
        job_description = job.get("description", "")
        
        # Skills: support both "skills" and separate required/optional
        job_all_skills = job.get("skills", [])
        job_required_skills = job.get("requiredSkills", job_all_skills)  # Default to all if not specified
        job_optional_skills = job.get("optionalSkills", [])
        
        # Experience
        job_min_exp = job.get("minExperience")
        job_max_exp = job.get("maxExperience")
        
        if isinstance(job_min_exp, str):
            job_min_exp = parse_experience(job_min_exp)
        if isinstance(job_max_exp, str):
            job_max_exp = parse_experience(job_max_exp)
        
        # ===== RUN MATCHING PIPELINE =====
        skills_result = skills_matcher.match(
            user_skills, 
            job_required_skills,
            job_optional_skills
        )
        
        title_result = title_matcher.match(user_title, job_title)
        
        experience_result = experience_matcher.match(
            user_experience,
            job_min_exp,
            job_max_exp
        )
        
        summary_result = summary_matcher.match(user_summary, job_description)
        
        # ===== AGGREGATE SCORES =====
        aggregated = ScoreAggregator.aggregate(
            skills_result,
            title_result,
            experience_result,
            summary_result
        )
        
        recommendations.append({
            "job_id": job_id,
            "score": aggregated["final_score"],
            "confidence": aggregated["confidence"],
            "breakdown": aggregated["breakdown"],
            "flags": aggregated["flags"]
        })
    
    # Sort by score (highest first)
    recommendations.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "recommendations": recommendations,
        "metadata": {
            "total_jobs": len(jobs),
            "user_experience_years": user_experience,
            "matching_strategy": "hybrid_semantic_rules_v1"
        }
    }
