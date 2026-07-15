"""Data models for the Reels policy compliance checker."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    """Overall pre-publish verdict for a Reel."""

    PASS = "pass"                      # 未發現問題
    REVIEW = "review"                  # 小問題，建議調整
    REACH_RISK = "reach_risk"          # 有被限流（降低觸及）的風險
    VIOLATION_RISK = "violation_risk"  # 可能違反社群守則，有下架/停權風險


class Consequence(str, Enum):
    """What kind of penalty a rule hit points to."""

    REMOVAL = "removal"  # 違反社群守則：內容下架、帳號警告/停權
    REACH = "reach"      # 違反推薦準則/垃圾訊號：不被推薦、限流
    QUALITY = "quality"  # 品質/最佳實務建議：不罰，但影響表現


class Severity(str, Enum):
    """Severity of an individual detection."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


SEVERITY_WEIGHT = {
    Severity.LOW: 8,
    Severity.MEDIUM: 18,
    Severity.HIGH: 35,
    Severity.CRITICAL: 60,
}


@dataclass
class ReelContent:
    """Input content for one Reel you are about to publish.

    All fields are optional — the analyzer works with whatever is provided.
    Hashtags written inside the caption (``#foo``) are extracted automatically;
    the ``hashtags`` field is for tags you plan to add separately.
    """

    url: str = ""
    caption: str = ""
    hashtags: list[str] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    author_username: str = ""
    audio_transcript: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "ReelContent":
        return cls(
            url=data.get("url", ""),
            caption=data.get("caption", ""),
            hashtags=list(data.get("hashtags", [])),
            comments=list(data.get("comments", [])),
            author_username=data.get("author_username", ""),
            audio_transcript=data.get("audio_transcript", ""),
        )

    def text_fields(self) -> list[tuple[str, str]]:
        """Return (field_name, text) pairs for every non-empty text source."""
        fields: list[tuple[str, str]] = []
        if self.caption:
            fields.append(("caption", self.caption))
        if self.audio_transcript:
            fields.append(("audio_transcript", self.audio_transcript))
        for i, comment in enumerate(self.comments):
            if comment:
                fields.append((f"comment[{i}]", comment))
        if self.hashtags:
            fields.append(("hashtags", " ".join(f"#{h.lstrip('#')}" for h in self.hashtags)))
        return fields


@dataclass
class Detection:
    """A single policy finding."""

    category: str
    consequence: Consequence
    severity: Severity
    rule_id: str
    message: str
    suggestion: str
    field: str
    evidence: str

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "consequence": self.consequence.value,
            "severity": self.severity.value,
            "rule_id": self.rule_id,
            "message": self.message,
            "suggestion": self.suggestion,
            "field": self.field,
            "evidence": self.evidence,
        }


@dataclass
class AnalysisResult:
    """Aggregated pre-publish analysis of one Reel."""

    verdict: Verdict
    risk_score: int  # 0-100
    detections: list[Detection]
    categories: dict[str, int]  # category -> contribution to score

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict.value,
            "risk_score": self.risk_score,
            "categories": self.categories,
            "detections": [d.to_dict() for d in self.detections],
        }
