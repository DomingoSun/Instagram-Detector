import json

import pytest

from reels_safety.cli import main


def test_safe_caption_exits_zero(capsys):
    assert main(["--caption", "lovely day at the park"]) == 0
    out = capsys.readouterr().out
    assert "SAFE" in out


def test_unsafe_caption_exits_nonzero(capsys):
    code = main(["--caption", "free bitcoin giveaway!! dm me to invest https://t.me/x"])
    assert code == 1
    out = capsys.readouterr().out
    assert "UNSAFE" in out


def test_json_output(capsys):
    main(["--caption", "guaranteed profit weekly", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] in {"caution", "unsafe"}
    assert payload["risk_score"] > 0


def test_json_file_input(tmp_path, capsys):
    reel = {
        "caption": "normal caption",
        "comments": ["kys"],
    }
    path = tmp_path / "reel.json"
    path.write_text(json.dumps(reel), encoding="utf-8")
    code = main(["--json-file", str(path), "--format", "json"])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "unsafe"


def test_no_content_errors():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
