"""Command-line interface for the Reels safety detector.

Usage examples:

    reels-safety --caption "Double your money! DM me to invest"
    reels-safety --json-file reel.json --format json
    echo "free bitcoin giveaway t.me/xyz" | reels-safety --stdin
"""

from __future__ import annotations

import argparse
import json
import sys

from reels_safety import __version__
from reels_safety.analyzer import analyze
from reels_safety.models import AnalysisResult, ReelContent, Verdict

_VERDICT_LABEL = {
    Verdict.SAFE: "SAFE",
    Verdict.CAUTION: "CAUTION",
    Verdict.UNSAFE: "UNSAFE",
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reels-safety",
        description="Analyze Instagram Reels content for safety risks.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--url", default="", help="Reel URL (metadata only, not fetched)")
    parser.add_argument("--caption", default="", help="Reel caption text")
    parser.add_argument("--transcript", default="", help="Audio transcript text")
    parser.add_argument(
        "--comment",
        action="append",
        default=[],
        dest="comments",
        help="A comment to analyze (repeatable)",
    )
    parser.add_argument(
        "--hashtag",
        action="append",
        default=[],
        dest="hashtags",
        help="A hashtag to analyze (repeatable)",
    )
    parser.add_argument(
        "--json-file",
        help="Path to a JSON file with reel content "
        "(keys: url, caption, hashtags, comments, author_username, audio_transcript)",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read caption text from standard input",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    return parser


def _render_text(result: AnalysisResult) -> str:
    lines = [
        f"Verdict:    {_VERDICT_LABEL[result.verdict]}",
        f"Risk score: {result.risk_score}/100",
    ]
    if result.categories:
        lines.append("Categories:")
        for category, weight in sorted(result.categories.items(), key=lambda kv: -kv[1]):
            lines.append(f"  - {category} (+{weight})")
    if result.detections:
        lines.append("Detections:")
        for det in result.detections:
            lines.append(f"  [{det.severity.value.upper():>8}] {det.message}")
            lines.append(f"           rule: {det.rule_id}  field: {det.field}")
            lines.append(f"           evidence: {det.evidence!r}")
    else:
        lines.append("No safety issues detected.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.json_file:
        try:
            with open(args.json_file, encoding="utf-8") as fh:
                content = ReelContent.from_dict(json.load(fh))
        except (OSError, json.JSONDecodeError) as exc:
            parser.error(f"cannot read {args.json_file}: {exc}")
    else:
        caption = args.caption
        if args.stdin:
            caption = (caption + "\n" + sys.stdin.read()).strip()
        content = ReelContent(
            url=args.url,
            caption=caption,
            hashtags=args.hashtags,
            comments=args.comments,
            audio_transcript=args.transcript,
        )

    if not content.text_fields():
        parser.error("no content to analyze — provide --caption, --comment, --json-file, or --stdin")

    result = analyze(content)
    if args.format == "json":
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(_render_text(result))

    return 0 if result.verdict is Verdict.SAFE else 1


if __name__ == "__main__":
    sys.exit(main())
