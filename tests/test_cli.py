# -*- coding: utf-8 -*-
import json

import pytest

from reels_safety.cli import main


def test_clean_caption_exits_zero(capsys):
    assert main(["--caption", "今天的拍攝日常 #vlog #攝影"]) == 0
    out = capsys.readouterr().out
    assert "通過" in out
    assert "人工檢查清單" in out


def test_reach_risk_exits_one(capsys):
    code = main(["--caption", "按讚+分享+標記朋友就抽獎！"])
    assert code == 1
    out = capsys.readouterr().out
    assert "限流風險" in out
    assert "建議:" in out


def test_violation_risk_exits_two(capsys):
    code = main(["--caption", "娛樂城註冊就送888"])
    assert code == 2
    assert "違規風險" in capsys.readouterr().out


def test_no_checklist_flag(capsys):
    main(["--caption", "普通內容", "--no-checklist"])
    assert "人工檢查清單" not in capsys.readouterr().out


def test_json_output(capsys):
    main(["--caption", "7天瘦5公斤保證有效", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "reach_risk"
    assert payload["risk_score"] > 0
    assert payload["detections"][0]["suggestion"]


def test_json_file_input(tmp_path, capsys):
    reel = {
        "caption": "新影片上線！",
        "hashtags": ["tagsforlikes", "fitness"],
        "audio_transcript": "跟著做保證獲利穩賺不賠",
    }
    path = tmp_path / "reel.json"
    path.write_text(json.dumps(reel, ensure_ascii=False), encoding="utf-8")
    code = main(["--json-file", str(path), "--format", "json"])
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "violation_risk"


def test_no_content_errors():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
