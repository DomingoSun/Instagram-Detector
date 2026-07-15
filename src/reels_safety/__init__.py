"""Reels policy checker — 發佈前檢查 Instagram Reels 內容的限流與違規風險。"""

from reels_safety.analyzer import analyze, collect_hashtags
from reels_safety.models import (
    AnalysisResult,
    Consequence,
    Detection,
    ReelContent,
    Verdict,
)
from reels_safety.rules import MANUAL_CHECKLIST

__version__ = "0.2.0"

__all__ = [
    "analyze",
    "collect_hashtags",
    "AnalysisResult",
    "Consequence",
    "Detection",
    "ReelContent",
    "Verdict",
    "MANUAL_CHECKLIST",
    "__version__",
]
