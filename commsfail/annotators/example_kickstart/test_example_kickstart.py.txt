"""Behaviour of example_kickstart: which posts it points at, which mode, and why. Replace these expectations with yours."""
from pathlib import Path
from commsfail.annotators import registry
from commsfail.sources import sharednet

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

def _found(out):
    return [(f["seq"], f["mode"]) for f in out["findings"]]

def test_example_kickstart_on_the_synthetic_room(synthetic_trace):
    out = registry()["example_kickstart"]().annotate(synthetic_trace)
    assert _found(out) == [
        (2, "open_question"),        # B asks for the tests to be run; nobody answers or cites it
        (11, "open_question"),       # "maybe someone could take `cli.ts`?" is left hanging
    ]

def test_example_kickstart_on_the_goal_run_sample():
    out = registry()["example_kickstart"]().annotate(sharednet.load(str(FIXTURES / "goal_run")))
    assert _found(out) == [
        (6, "open_question"),        # codex-2 asks codex-1 about an empty file; codex-1 never answers
        (10, "bare_claim"),          # codex-1 says DONE and names nothing a reader could check
    ]

def test_example_kickstart_on_the_share_sample():
    out = registry()["example_kickstart"]().annotate(sharednet.load(str(FIXTURES / "share.json")))
    assert _found(out) == []         # #2's question is answered by #3, which cites it; #4 names `cli.py`
