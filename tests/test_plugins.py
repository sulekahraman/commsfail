"""Plugin discovery: an entry point becomes a registered annotator or loader; a broken one is skipped, not fatal."""
import warnings
from importlib.metadata import EntryPoint
from pathlib import Path
import pytest
import commsfail._plugins as plugins
from commsfail import annotators, loaders, validate

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "plugin"

def _entry_points(*eps):
    return lambda group: [ep for ep in eps if ep.group == group]

def test_example_plugin_registers_an_annotator_and_a_loader(monkeypatch, synthetic_trace):
    monkeypatch.syspath_prepend(str(EXAMPLE))
    monkeypatch.setattr(plugins, "entry_points", _entry_points(
        EntryPoint("example_v1", "commsfail_example:ExampleV1", annotators.ENTRY_POINT_GROUP),
        EntryPoint("chat_jsonl", "commsfail_example:load_chat_jsonl", loaders.ENTRY_POINT_GROUP)))
    reg = annotators.discover()
    assert set(reg) >= {"regex_v1", "example_v1"}
    assert validate(reg["example_v1"]().annotate(synthetic_trace)) == []
    lds = loaders.discover()
    assert "auto" in lds
    trace = lds["chat_jsonl"](str(EXAMPLE / "sample_chat.jsonl"))
    assert trace.source["kind"] == "chat-jsonl" and [p["seq"] for p in trace.posts] == [1, 2, 3, 4, 5]
    out = reg["example_v1"]().annotate(trace)
    assert validate(out) == [] and next(m for m in out["modes"] if m["id"] == "D3")["present"]
    assert validate(reg["regex_v1"]().annotate(trace)) == []

def test_a_broken_plugin_is_skipped_with_a_warning(monkeypatch):
    monkeypatch.setattr(plugins, "entry_points", _entry_points(
        EntryPoint("broken", "no_such_module_for_commsfail:Nope", annotators.ENTRY_POINT_GROUP)))
    with pytest.warns(RuntimeWarning, match="broken"):
        reg = annotators.discover()
    assert set(reg) == set(annotators.BUILTIN)

def test_a_plugin_class_is_keyed_by_its_own_name(monkeypatch):
    monkeypatch.setattr(plugins, "entry_points", _entry_points(
        EntryPoint("whatever", "commsfail.annotators.regex_v1:RegexV1", annotators.ENTRY_POINT_GROUP)))
    with warnings.catch_warnings():
        warnings.simplefilter("error")          # the same class under its own name is not a replacement
        reg = annotators.discover()
    assert set(reg) == {"regex_v1"}
