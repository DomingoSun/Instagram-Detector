"""Core analysis engine: run rules over Reel content and aggregate a verdict."""

from __future__ import annotations

from urllib.parse import urlparse

from reels_safety import rules
from reels_safety.models import (
    SEVERITY_WEIGHT,
    AnalysisResult,
    Detection,
    ReelContent,
    Severity,
    Verdict,
)

# Verdict thresholds on the 0-100 risk score.
CAUTION_THRESHOLD = 20
UNSAFE_THRESHOLD = 55

# Any single CRITICAL detection forces an UNSAFE verdict regardless of score.
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
                    severity=rule.severity,
                    rule_id=rule.rule_id,
                    message=rule.message,
                    field=field,
                    evidence=_snippet(text, match.start(), match.end()),
                )
            )
    return detections


def _domain_of(url: str) -> str:
    if not url.lower().startswith(("http://", "https://")):
        url = "http://" + url
    return (urlparse(url).hostname or "").lower().lstrip("www.")


def _run_url_rules(field: str, text: str) -> list[Detection]:
    detections = []
    for match in rules.URL_PATTERN.finditer(text):
        url = match.group(0)
        domain = _domain_of(url)
        if not domain:
            continue

        if rules.LOOKALIKE_PATTERN.search(url):
            detections.append(
                Detection(
                    category=rules.PHISHING,
                    severity=Severity.HIGH,
                    rule_id="phishing.lookalike_domain",
                    message="Link uses a lookalike domain impersonating a known platform",
                    field=field,
                    evidence=url[:_MAX_EVIDENCE_LEN],
                )
            )
            continue

        if domain in rules.URL_SHORTENERS:
            detections.append(
                Detection(
                    category=rules.PHISHING,
                    severity=Severity.LOW,
                    rule_id="phishing.shortened_url",
                    message="Shortened/redirect link hides its real destination",
                    field=field,
                    evidence=url[:_MAX_EVIDENCE_LEN],
                )
            )

        if any(domain == d or domain.endswith("." + d) for d in rules.MESSAGING_APP_DOMAINS):
            severity = (
                Severity.HIGH if rules.MONEY_CONTEXT.search(text) else Severity.MEDIUM
            )
            detections.append(
                Detection(
                    category=rules.PHISHING,
                    severity=severity,
                    rule_id="phishing.offplatform_messaging",
                    message=(
                        "Pushes viewers to an off-platform messaging app"
                        + (" in a money-making context" if severity is Severity.HIGH else "")
                    ),
                    field=field,
                    evidence=url[:_MAX_EVIDENCE_LEN],
                )
            )
    return detections


def analyze(content: ReelContent) -> AnalysisResult:
    """Analyze Reel content and return a scored safety verdict."""
    detections: list[Detection] = []
    for field, text in content.text_fields():
        detections.extend(_run_text_rules(field, text))
        detections.extend(_run_url_rules(field, text))

    # Score: sum severity weights, but count each rule_id once per field to
    # avoid a single spammy comment thread dominating the score.
    seen: set[tuple[str, str]] = set()
    categories: dict[str, int] = {}
    score = 0
    for det in detections:
        key = (det.rule_id, det.field)
        if key in seen:
            continue
        seen.add(key)
        weight = SEVERITY_WEIGHT[det.severity]
        score += weight
        categories[det.category] = categories.get(det.category, 0) + weight

    score = min(score, 100)

    if any(d.severity is Severity.CRITICAL for d in detections) or score >= UNSAFE_THRESHOLD:
        verdict = Verdict.UNSAFE
    elif score >= CAUTION_THRESHOLD:
        verdict = Verdict.CAUTION
    else:
        verdict = Verdict.SAFE

    detections.sort(key=lambda d: SEVERITY_WEIGHT[d.severity], reverse=True)
    return AnalysisResult(
        verdict=verdict,
        risk_score=score,
        detections=detections,
        categories=categories,
    )
