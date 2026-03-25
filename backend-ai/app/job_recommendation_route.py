"""Compatibility facade for the job recommendation module.

This file keeps the original import path stable while delegating implementation
into smaller modules under ``app.job_recommendation``.
"""

from app.job_recommendation import (
    ExperienceMatcher,
    ScoreAggregator,
    SkillsMatcher,
    SummaryMatcher,
    TitleMatcher,
    cosine_sim,
    get_model,
    normalize_skill,
    parse_experience,
    recommend,
    recommend_for_job,
    router,
)

__all__ = [
    "router",
    "recommend",
    "recommend_for_job",
    "get_model",
    "cosine_sim",
    "normalize_skill",
    "parse_experience",
    "SkillsMatcher",
    "TitleMatcher",
    "ExperienceMatcher",
    "SummaryMatcher",
    "ScoreAggregator",
]
