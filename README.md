# Instagram Reels Safety Detector (MVP)

A lightweight, dependency-free Python library and CLI that analyzes Instagram
Reels content — caption, hashtags, comments, audio transcript, and embedded
links — and flags safety risks with a 0–100 risk score and an overall verdict
(`safe` / `caution` / `unsafe`).

Built for **defensive** use: content moderation, parental review, and brand
safety screening.

## What it detects

| Category | Examples |
| --- | --- |
| `scam_fraud` | Guaranteed-return investment pitches, crypto giveaways, cash-app "flips", advance-fee prize claims, "DM me to invest" |
| `phishing_links` | Lookalike domains (`1nstagram-…`, `paypa1…`), URL shorteners hiding destinations, off-platform pushes to Telegram/WhatsApp in money-making contexts |
| `dangerous_challenge` | Known harmful viral challenges (blackout, benadryl, fire, skull-breaker…) |
| `adult_content` | Explicit-content solicitation and keywords |
| `self_harm` | Suicide/self-harm encouragement and promotion (any hit forces `unsafe`) |
| `hate_harassment` | Direct threats of violence, doxxing (threats force `unsafe`) |
| `spam_engagement_bait` | Follow-for-reward bait, follower-buying, high-pressure "link in bio" |

## Install

```bash
pip install -e ".[dev]"
```

No runtime dependencies — pure standard library (Python ≥ 3.9).

## CLI usage

```bash
# Analyze a caption directly
reels-safety --caption "Double your money! DM me to invest https://t.me/signals"

# Analyze a full reel from JSON, get machine-readable output
reels-safety --json-file examples/scam_reel.json --format json

# Pipe text in
echo "free bitcoin giveaway" | reels-safety --stdin
```

Exit code is `0` for a `safe` verdict and `1` otherwise, so it slots into
moderation pipelines and shell scripts.

Sample output:

```
Verdict:    UNSAFE
Risk score: 100/100
Categories:
  - scam_fraud (+88)
  - phishing_links (+35)
Detections:
  [    HIGH] Promises of guaranteed or doubled returns, a hallmark of investment scams
           rule: scam.guaranteed_returns  field: caption
           evidence: 'Double your money in 7 days! Guaranteed profit'
  ...
```

## JSON input schema

```json
{
  "url": "https://www.instagram.com/reel/…/",
  "caption": "…",
  "hashtags": ["…"],
  "comments": ["…"],
  "author_username": "…",
  "audio_transcript": "…"
}
```

All fields are optional; the analyzer uses whatever is provided. Fetching this
data from Instagram is out of scope for the MVP — bring your own extraction
(official APIs, exports, or manual input).

## Library usage

```python
from reels_safety import ReelContent, analyze

result = analyze(ReelContent(caption="guaranteed profit, dm me to invest"))
print(result.verdict.value)   # "unsafe"
print(result.risk_score)      # e.g. 70
for det in result.detections:
    print(det.category, det.severity.value, det.message)
```

## How scoring works

Each rule hit contributes a severity weight (low 8, medium 18, high 35,
critical 60). A rule counts once per field so one spammy comment can't
dominate. The total is capped at 100:

- **< 20** → `safe`
- **20–54** → `caution`
- **≥ 55**, or any `critical` hit → `unsafe`

Rules are intentionally precision-first: obviously risky patterns fire; benign
content stays clean. Tune thresholds in `analyzer.py` and add rules in
`rules.py`.

## Running tests

```bash
python -m pytest
```

## Roadmap ideas

- LLM-assisted semantic analysis for context the regex rules miss
- Image/video-frame analysis
- Batch mode + CSV report output
- Configurable rule packs and per-category thresholds
