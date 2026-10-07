"""example_kickstart: open questions and bare claims, as a starting point. Replace annotate() with your method.

``commsfail new <name>`` copies this folder. Keep three rules: the same trace gives the same output,
annotate() uses no network, and every excerpt of post text goes through redact(). The modes it reports are
in taxonomy.json; change them there, and keep schema.json and modes_in() in step.
"""
from __future__ import annotations
import re
from commsfail.annotators.taxonomy import taxonomy_of
from commsfail.sources.sharednet import agent_posts, cites, redact
from commsfail.trace import Trace

DONE_RE = re.compile(r"\b(?:done|finished|complete[d]?|pass(?:es|ed)?|ready)\b", re.I)
# something a reader could check: a backticked item, a file name, or a post number
CHECKABLE_RE = re.compile(r"`[^`]+`|\b[\w./-]+\.\w{1,5}\b|#\d+")

class ExampleKickstart:
    """Open questions and bare claims: a two-mode sample taxonomy. Replace this line with yours."""
    name = "example_kickstart"
    version = "0.1.0"
    schema = "schema.json"
    taxonomy = "taxonomy.json"

    def modes_in(self, output: dict) -> list[str]:
        return [f["mode"] for f in output["findings"]]

    def annotate(self, trace: Trace) -> dict:
        tax = taxonomy_of(self)
        why = {m["id"]: m["definition"] for m in tax["modes"]}
        posts = agent_posts(trace)
        answered = set()
        for p in posts:
            if p.get("reply_to"):
                answered.add(p["reply_to"])
            answered.update(cites(p["text"]))
        findings = []
        for p in posts:
            text = p["text"].rstrip()
            if text.endswith("?") and p["seq"] not in answered:
                findings.append(("open_question", p))
            if DONE_RE.search(text) and not CHECKABLE_RE.search(text):
                findings.append(("bare_claim", p))
        rows = [{"seq": p["seq"], "who": p["who"], "mode": mode, "excerpt": redact(p["text"]), "why": why[mode]}
                for mode, p in findings]
        counts = {"posts": len(posts), **{m: sum(1 for r in rows if r["mode"] == m) for m in why}}
        return {"taxonomy": f"{tax['id']}@{tax['version']}", "findings": rows, "counts": counts}

    def markdown(self, output: dict) -> str:
        c = output["counts"]
        lines = [f"{c['open_question']} open question(s) and {c['bare_claim']} bare claim(s) in {c['posts']} posts", ""]
        lines += [f"- #{f['seq']} {f['who']} ({f['mode']}): {f['excerpt']}" for f in output["findings"]]
        return "\n".join(lines)

ANNOTATOR = ExampleKickstart
