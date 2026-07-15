"""發佈前政策檢查 CLI。

用法範例：

    reels-safety --caption "按讚+分享抽AirPods！ #f4f #tagsforlikes"
    reels-safety --json-file examples/risky_reel.json --format json
    echo "7天瘦5公斤 保證有效" | reels-safety --stdin
"""

from __future__ import annotations

import argparse
import json
import sys

from reels_safety import __version__
from reels_safety.analyzer import analyze
from reels_safety.models import AnalysisResult, ReelContent, Verdict
from reels_safety.rules import MANUAL_CHECKLIST

_VERDICT_LABEL = {
    Verdict.PASS: "✅ 通過 — 未發現政策問題",
    Verdict.REVIEW: "🔍 建議調整 — 有小問題但風險低",
    Verdict.REACH_RISK: "⚠️ 限流風險 — 內容可能不被推薦、觸及下降",
    Verdict.VIOLATION_RISK: "🚫 違規風險 — 可能被下架或影響帳號",
}

_SEVERITY_LABEL = {"low": "低", "medium": "中", "high": "高", "critical": "嚴重"}
_CONSEQUENCE_LABEL = {
    "removal": "下架/帳號處分",
    "reach": "限流",
    "quality": "最佳實務",
}

_EXIT_CODE = {
    Verdict.PASS: 0,
    Verdict.REVIEW: 0,
    Verdict.REACH_RISK: 1,
    Verdict.VIOLATION_RISK: 2,
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reels-safety",
        description="發佈前檢查 Reels 內容是否有違反 Instagram 政策、被限流或下架的風險。",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--url", default="", help="Reel 網址（僅記錄，不會抓取）")
    parser.add_argument("--caption", default="", help="貼文文案（含 #hashtag 會自動解析）")
    parser.add_argument("--transcript", default="", help="影片口白/字幕逐字稿")
    parser.add_argument(
        "--comment",
        action="append",
        default=[],
        dest="comments",
        help="要一併檢查的留言（可重複使用）",
    )
    parser.add_argument(
        "--hashtag",
        action="append",
        default=[],
        dest="hashtags",
        help="要使用的 hashtag（可重複使用）",
    )
    parser.add_argument(
        "--json-file",
        help="JSON 檔路徑（欄位：url, caption, hashtags, comments, audio_transcript）",
    )
    parser.add_argument("--stdin", action="store_true", help="從標準輸入讀取文案")
    parser.add_argument(
        "--no-checklist", action="store_true", help="不顯示人工檢查清單"
    )
    parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="輸出格式（預設 text）"
    )
    return parser


def _render_text(result: AnalysisResult, show_checklist: bool) -> str:
    lines = [
        f"判定:     {_VERDICT_LABEL[result.verdict]}",
        f"風險分數: {result.risk_score}/100",
    ]
    if result.detections:
        lines.append("")
        lines.append("發現的問題:")
        for det in result.detections:
            sev = _SEVERITY_LABEL[det.severity.value]
            cons = _CONSEQUENCE_LABEL[det.consequence.value]
            lines.append(f"  [{sev}｜{cons}] {det.message}")
            lines.append(f"      位置: {det.field}  證據: {det.evidence!r}")
            lines.append(f"      建議: {det.suggestion}")
    else:
        lines.append("")
        lines.append("文字內容未發現政策問題。")

    if show_checklist:
        lines.append("")
        lines.append("發佈前人工檢查清單（文字掃不到的部分）:")
        for item in MANUAL_CHECKLIST:
            lines.append(f"  □ {item}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.json_file:
        try:
            with open(args.json_file, encoding="utf-8") as fh:
                content = ReelContent.from_dict(json.load(fh))
        except (OSError, json.JSONDecodeError) as exc:
            parser.error(f"無法讀取 {args.json_file}: {exc}")
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
        parser.error("沒有可檢查的內容 — 請提供 --caption、--comment、--json-file 或 --stdin")

    result = analyze(content)
    if args.format == "json":
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(_render_text(result, show_checklist=not args.no_checklist))

    return _EXIT_CODE[result.verdict]


if __name__ == "__main__":
    sys.exit(main())
