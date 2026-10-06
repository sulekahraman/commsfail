"""Contract tests every registered annotator must pass. Add yours to the registry and these run on it too."""
import json
import pytest
from commsfail import REGISTRY, validate, MODES
from commsfail.annotators.base import Annotator

@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_annotator_output_conforms(name, synthetic_trace):
    ann = REGISTRY[name]()
    assert isinstance(ann, Annotator)
    out = ann.annotate(synthetic_trace)
    assert validate(out) == []
    assert {m["id"] for m in out["modes"]} == set(MODES)
    json.dumps(out)  # must be serializable

@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_annotator_is_deterministic(name, synthetic_trace):
    ann = REGISTRY[name]()
    a, b = ann.annotate(synthetic_trace), ann.annotate(synthetic_trace)
    a["source"].pop("fetched_at", None); b["source"].pop("fetched_at", None)
    assert a == b

@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_evidence_points_at_real_posts(name, synthetic_trace):
    out = REGISTRY[name]().annotate(synthetic_trace)
    seqs = {p["seq"] for p in synthetic_trace.posts} | {0}
    for m in out["modes"]:
        for e in m["evidence"]:
            assert e["seq"] in seqs, f"{m['id']} evidence points at a post that does not exist: {e['seq']}"
            assert "shr_" not in e["excerpt"] and "snk_" not in e["excerpt"], "tokens must be redacted"
