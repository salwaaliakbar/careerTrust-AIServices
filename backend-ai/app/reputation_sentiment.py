from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Dict

import torch
import torch.nn as nn
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from transformers import DistilBertConfig, DistilBertModel, DistilBertTokenizerFast


class ReviewSentimentRequest(BaseModel):
    review_text: str = Field(..., min_length=5, max_length=4000)


class MultiAspectRegressor(nn.Module):
    def __init__(self, hidden_dim: int, aspect_names: list[str]):
        super().__init__()
        self.encoder = DistilBertModel(DistilBertConfig())
        self.feature_extractor = nn.Sequential(
            nn.Linear(self.encoder.config.hidden_size, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.35),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.35),
        )

        head_hidden = max(hidden_dim // 2, 64)
        self.overall_head = nn.Sequential(
            nn.Linear(hidden_dim, head_hidden),
            nn.GELU(),
            nn.Dropout(0.2),
            nn.Linear(head_hidden, 1),
        )

        self.aspect_heads = nn.ModuleDict(
            {
                aspect: nn.Sequential(
                    nn.Linear(hidden_dim, head_hidden),
                    nn.GELU(),
                    nn.Dropout(0.2),
                    nn.Linear(head_hidden, 1),
                )
                for aspect in aspect_names
            }
        )

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor):
        encoded = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        pooled = encoded.last_hidden_state[:, 0, :]
        features = self.feature_extractor(pooled)

        overall = self.overall_head(features).squeeze(-1)
        aspects = {
            name: head(features).squeeze(-1) for name, head in self.aspect_heads.items()
        }
        return overall, aspects


class SentimentInferenceService:
    def __init__(self):
        self._lock = Lock()
        self._ready = False
        self._model = None
        self._tokenizer = None
        self._aspect_names: list[str] = []
        self._rating_min = 1.0
        self._rating_max = 5.0

    def _model_dir(self) -> Path:
        return (
            Path(__file__).resolve().parents[1]
            / "model_output_v3"
            / "model_output_v3"
        )

    def _load(self):
        model_dir = self._model_dir()
        config_path = model_dir / "config.json"
        weight_path = model_dir / "best.pt"

        if not config_path.exists() or not weight_path.exists():
            raise RuntimeError("Model files missing in model_output_v3/model_output_v3")

        with config_path.open("r", encoding="utf-8") as f:
            cfg = json.load(f)

        self._aspect_names = cfg.get("aspect_names", [])
        hidden_dim = int(cfg.get("hidden_dim", 384))
        self._rating_min = float(cfg.get("rating_min", 1.0))
        self._rating_max = float(cfg.get("rating_max", 5.0))

        if not self._aspect_names:
            raise RuntimeError("aspect_names missing in sentiment config")

        self._tokenizer = DistilBertTokenizerFast.from_pretrained(
            str(model_dir),
            local_files_only=True,
        )

        model = MultiAspectRegressor(hidden_dim=hidden_dim, aspect_names=self._aspect_names)
        checkpoint = torch.load(weight_path, map_location="cpu")

        if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
            state_dict = checkpoint["state_dict"]
        else:
            state_dict = checkpoint

        model.load_state_dict(state_dict, strict=False)
        model.eval()

        self._model = model
        self._ready = True

    def ensure_ready(self):
        if self._ready:
            return
        with self._lock:
            if self._ready:
                return
            self._load()

    def analyze(self, review_text: str) -> Dict[str, object]:
        self.ensure_ready()
        assert self._tokenizer is not None
        assert self._model is not None

        encoded = self._tokenizer(
            review_text,
            truncation=True,
            padding="max_length",
            max_length=256,
            return_tensors="pt",
        )

        with torch.no_grad():
            overall, aspects = self._model(
                encoded["input_ids"],
                encoded["attention_mask"],
            )

        overall_score = float(overall[0].item())
        overall_score = max(self._rating_min, min(self._rating_max, overall_score))

        aspect_scores: Dict[str, float] = {}
        for name in self._aspect_names:
            value = float(aspects[name][0].item())
            aspect_scores[name] = max(self._rating_min, min(self._rating_max, value))

        return {
            "overall_score": round(overall_score, 3),
            "aspect_scores": {k: round(v, 3) for k, v in aspect_scores.items()},
            "rating_min": self._rating_min,
            "rating_max": self._rating_max,
            "model": "model_output_v3",
        }


_service = SentimentInferenceService()
router = APIRouter()


@router.post("/analyze-review-sentiment")
def analyze_review_sentiment(payload: ReviewSentimentRequest):
    text = payload.review_text.strip()
    if len(text) < 5:
        raise HTTPException(status_code=400, detail="review_text is too short")

    try:
        return _service.analyze(text)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Sentiment analysis failed: {error}")
