"""template_name: open questions, as a starting point. Replace annotate() with your method.

Made by `commsfail new template_name`. Keep three rules: the same trace gives the same output, annotate()
uses no network, and every excerpt of post text goes through redact().
"""
from __future__ import annotations
from commsfail.sources.sharednet import agent_posts, cites, redact
from commsfail.trace import Trace

class TemplateName:
    """Open questions: posts that ask something no later post answers or cites. Replace this line with yours."""
    name = "template_name"
    version = "0.1.0"
    schema = "schema.json"

    def annotate(self, trace: Trace) -> dict:
        posts = agent_posts(trace)
        answered = set()
        for p in posts:
            if p.get("reply_to"):
                answered.add(p["reply_to"])
            answered.update(cites(p["text"]))
        questions = [p for p in posts if p["text"].rstrip().endswith("?")]
        findings = [{"seq": p["seq"], "who": p["who"], "label": "open_question", "excerpt": redact(p["text"]),
                     "why": "asks a question that no later post answers or cites"}
                    for p in questions if p["seq"] not in answered]
        return {"findings": findings, "counts": {"posts": len(posts), "questions": len(questions), "open": len(findings)}}

    def markdown(self, output: dict) -> str:
        c = output["counts"]
        lines = [f"{c['open']} open question(s) of {c['questions']}, in {c['posts']} posts", ""]
        lines += [f"- #{f['seq']} {f['who']}: {f['excerpt']}" for f in output["findings"]]
        return "\n".join(lines)

ANNOTATOR = TemplateName
