"""The command line: listing, analysing to a file, validating with exit codes."""
import json
from commsfail.cli import main

def test_annotators_lists_the_reference(capsys):
    assert main(["annotators"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("regex_v1") or "\nregex_v1" in out
    assert "builtin" in out

def test_loaders_lists_auto(capsys):
    assert main(["loaders"]) == 0
    assert "auto" in capsys.readouterr().out

def test_analyse_writes_a_conforming_record(tmp_path, capsys):
    share = {"room": {"name": "r", "created_at": "2026-09-20T10:00:00Z", "latest_sequence": 2},
             "members": [{"handle": "A", "driver": "claude-code", "joined_at": "2026-09-20T10:00:00Z"}],
             "messages": [{"sequence": 1, "content": "I'll take `a.py`.", "created_at": "2026-09-20T10:01:00Z", "sender": {"handle": "A"}},
                          {"sequence": 2, "content": "`a.py` is done.", "created_at": "2026-09-20T10:02:00Z", "sender": {"handle": "A"}}]}
    src = tmp_path / "share.json"; src.write_text(json.dumps(share), encoding="utf-8")
    out = tmp_path / "out.json"
    assert main(["analyse", str(src), "-o", str(out)]) == 0
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert rec["schema"] == "comms-failure/analysis.v1" and rec["source"]["annotator"].startswith("regex_v1@")
    assert "a.py" in rec["items"]
    assert main(["validate", str(out)]) == 0
    bad = tmp_path / "bad.json"; bad.write_text("{}", encoding="utf-8")
    assert main(["validate", str(bad)]) == 1
    assert main(["analyse", str(src), "--markdown"]) == 0
    assert "| mode | severity |" in capsys.readouterr().out
