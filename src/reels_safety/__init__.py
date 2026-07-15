"""Reels Safety Detector — analyze Instagram Reels content for safety risks."""

from reels_safety.analyzer import analyze
from reels_safety.models import AnalysisResult, Detection, ReelContent, Verdict

__version__ = "0.1.0"

__all__ = [
    "analyze",
    "AnalysisResult",
    "Detection",
    "ReelContent",
    "Verdict",
    "__version__",
]
