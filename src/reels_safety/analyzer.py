"""Core analysis engine: run policy rules over Reel content and aggregate a verdict."""

from __future__ import annotations

from reels_safety import rules
from reels_safety.models import (
    SEVERITY_WEIGHT,
    AnalysisResult,
    Consequence,
    Detection,
    ReelContent,
    Severity,
    Verdict,
)

# 限流判定門檻：REACH 類加權總分達此值視為有限流風險
REACH_SCORE_THRESHOLD = 30

_MAX_EVIDENCE_LEN = 120


def _snippet(text: str, start: int, end: int) -> str:
    lo = max(0, start - 20)
    hi = min(len(text), end + 20)
    snippet = text[lo:hi].strip().replace("\n", " ")
    if len(snippet) > _MAX_EVIDENCE_LEN:
        snippet = snippet[:_MAX_EVIDENCE_LEN] + "…"
    return snippet


def _run_text_rules(field: str, text: str) -> list[Detection]:
    detections = []
    for rule in rules.TEXT_RULES:
        match = rule.pattern.search(text)
        if match:
            detections.append(
                Detection(
                    category=rule.category,
                    consequence=rule.consequence,
                    severity=rule.severity,
                    rule_id=rule.rule_id,
                    message=rule.message,
                    suggestion=rule.suggestion,
                    field=field,
                    evidence=_snippet(text, match.start(), match.end()),
                )
            )
    return detections


def collect_hashtags(content: ReelContent) -> list[str]:
    """All hashtags: explicit ``hashtags`` field plus ``#tags`` found in the caption."""
    tags = [h.lstrip("#").lower() for h in content.hashtags if h.strip("#")]
    tags += [m.group(1).lower() for m in rules.HASHTAG_IN_TEXT.finditer(content.caption)]
    return tags


def _check_hashtags(content: ReelContent) -> list[Detection]:
    tags = collect_hashtags(content)
    if not tags:
        return []

    detections: list[Detection] = []

    def det(severity: Severity, rule_id: str, message: str, suggestion: str, evidence: str):
        detections.append(
            Detection(
                category=rules.HASHTAG,
                consequence=Consequence.REACH,
                severity=severity,
                rule_id=rule_id,
                message=message,
                suggestion=suggestion,
                field="hashtags",
                evidence=evidence,
            )
        )

    if len(tags) > rules.HASHTAG_HARD_LIMIT:
        det(
            Severity.HIGH,
            "hashtag.over_hard_limit",
            f"共 {len(tags)} 個 hashtag，超過 Instagram 上限 {rules.HASHTAG_HARD_LIMIT} 個，"
            "貼文可能無法發佈或被直接判為垃圾內容",
            "刪減到 3–5 個最相關的標籤",
            f"{len(tags)} tags",
        )
    elif len(tags) > rules.HASHTAG_RECOMMENDED_MAX:
        det(
            Severity.LOW,
            "hashtag.too_many",
            f"共 {len(tags)} 個 hashtag，堆疊大量標籤是垃圾內容訊號",
            "官方建議 3–5 個精準標籤，效果優於大量廣撒",
            f"{len(tags)} tags",
        )

    restricted = sorted(set(tags) & rules.RESTRICTED_HASHTAGS)
    if restricted:
        det(
            Severity.MEDIUM,
            "hashtag.restricted",
            "使用了曾被回報遭封鎖/限制的 hashtag，貼文可能不會出現在標籤頁與推薦中",
            "發佈前到 IG 搜尋該標籤：若標籤頁顯示異常或搜不到，就換掉；清單會隨時間變動",
            ", ".join(f"#{t}" for t in restricted),
        )

    seen: set[str] = set()
    dupes = sorted({t for t in tags if t in seen or seen.add(t)})
    if dupes:
        det(
            Severity.LOW,
            "hashtag.duplicates",
            "有重複的 hashtag",
            "移除重複標籤，重複堆疊沒有加成、只有垃圾訊號",
            ", ".join(f"#{t}" for t in dupes),
        )

    return detections


def analyze(content: ReelContent) -> AnalysisResult:
    """Analyze Reel content and return a pre-publish policy verdict."""
    detections: list[Detection] = []
    for field, text in content.text_fields():
        detections.extend(_run_text_rules(field, text))
    detections.extend(_check_hashtags(content))

    # Score: sum severity weights, counting each rule_id once per field so a
    # repeated phrase can't dominate the score.
    seen: set[tuple[str, str]] = set()
    categories: dict[str, int] = {}
    score = 0
    reach_score = 0
    for det in detections:
        key = (det.rule_id, det.field)
        if key in seen:
            continue
        seen.add(key)
        weight = SEVERITY_WEIGHT[det.severity]
        score += weight
        if det.consequence is not Consequence.QUALITY:
            categories[det.category] = categories.get(det.category, 0) + weight
        if det.consequence is Consequence.REACH:
            reach_score += weight

    score = min(score, 100)

    removal_hits = [d for d in detections if d.consequence is Consequence.REMOVAL]
    if any(d.severity in (Severity.HIGH, Severity.CRITICAL) for d in removal_hits):
        verdict = Verdict.VIOLATION_RISK
    elif (
        removal_hits
        or reach_score >= REACH_SCORE_THRESHOLD
        or any(
            d.consequence is Consequence.REACH
            and d.severity in (Severity.MEDIUM, Severity.HIGH)
            for d in detections
        )
    ):
        verdict = Verdict.REACH_RISK
    elif detections:
        verdict = Verdict.REVIEW
    else:
        verdict = Verdict.PASS

    detections.sort(key=lambda d: SEVERITY_WEIGHT[d.severity], reverse=True)
    return AnalysisResult(
        verdict=verdict,
        risk_score=score,
        detections=detections,
        categories=categories,
    )
