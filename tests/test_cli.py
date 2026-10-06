"""The command line: listing, analysing to a record, validating, and starting a new annotator."""
import importlib.util, json, sys
from pathlib import Path
from commsfail.annotators import check_annotator, validate_output
from commsfail.cli import main
from commsfail.sources import sharednet

GOAL_RUN = str(Path(__file__).resolve().parent / "fixtures" / "goal_run")

def test_lists(capsys):
    assert main(["annotators"]) == 0
    out = capsys.readouterr().out
    assert "regex_v1" in out and "builtin" in out and "comms-failure/analysis.v1" in out
    assert main(["sources"]) == 0 and "sharednet" in capsys.readouterr().out

def test_analyse_validate_and_markdown(tmp_path, capsys):
    out = tmp_path / "rec.json"
    assert main(["analyse", GOAL_RUN, "-o", str(out)]) == 0
    rec = json.loads(out.read_text())
    assert rec["record"] == "commsfail/record.v1" and rec["annotator"]["name"] == "regex_v1"
    assert rec["source"]["kind"] == "goal-run" and rec["output"]["schema"] == "comms-failure/analysis.v1"
    assert main(["validate", str(out)]) == 0
    rec["output"]["modes"] = rec["output"]["modes"][:3]
    bad = tmp_path / "bad.json"; bad.write_text(json.dumps(rec))
    assert main(["validate", str(bad)]) == 1
    capsys.readouterr()
    assert main(["analyse", GOAL_RUN, "--markdown"]) == 0
    assert "| mode | severity |" in capsys.readouterr().out

def test_trace_and_schema(capsys):
    assert main(["trace", GOAL_RUN]) == 0
    assert json.loads(capsys.readouterr().out)["posts"] == 12
    assert main(["schema", "regex_v1"]) == 0
    assert json.loads(capsys.readouterr().out)["$id"] == "comms-failure/analysis.v1"

def test_new_makes_a_working_annotator(tmp_path, capsys, monkeypatch):
    (tmp_path / "commsfail" / "annotators").mkdir(parents=True)
    assert main(["new", "my_method_v1", "--root", str(tmp_path)]) == 0
    folder = tmp_path / "commsfail" / "annotators" / "my_method_v1"
    assert sorted(p.name for p in folder.iterdir()) == ["README.md", "__init__.py", "schema.json"]
    test = tmp_path / "tests" / "annotators" / "test_my_method_v1.py"
    compile(test.read_text(), str(test), "exec")
    assert "my_method_v1" in test.read_text() and "template_name" not in test.read_text()
    spec = importlib.util.spec_from_file_location("my_method_v1", folder / "__init__.py")
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "my_method_v1", mod)
    spec.loader.exec_module(mod)
    cls = mod.ANNOTATOR
    assert cls.__name__ == "MyMethodV1" and cls.name == "my_method_v1"
    assert check_annotator(cls) == []
    out = cls().annotate(sharednet.load(GOAL_RUN))
    assert validate_output(cls, out) == [] and [f["seq"] for f in out["findings"]] == [6]
    assert json.loads((folder / "schema.json").read_text())["$id"] == "commsfail/my_method_v1/v1"

def test_new_refuses_bad_names_and_existing_folders(tmp_path):
    import pytest
    (tmp_path / "commsfail" / "annotators").mkdir(parents=True)
    with pytest.raises(SystemExit):
        main(["new", "Bad-Name", "--root", str(tmp_path)])
    main(["new", "ok_v1", "--root", str(tmp_path)])
    with pytest.raises(SystemExit):
        main(["new", "ok_v1", "--root", str(tmp_path)])
    with pytest.raises(SystemExit):
        main(["new", "ok_v2", "--root", str(tmp_path / "nowhere")])
