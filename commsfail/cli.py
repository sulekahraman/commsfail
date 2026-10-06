"""commsfail command line.

    commsfail analyse <source> [--loader auto] [--annotator regex_v1] [--markdown] [-o out.json]
    commsfail annotators            list registered annotators, built in and plugins
    commsfail loaders               list registered loaders
    commsfail schema                print the analysis.v1 field documentation
    commsfail validate <file.json>  check a record against the schema; exit 1 if it does not conform

With the default loader, <source> is a SharedNet share link or token, a saved share JSON, a room export
NDJSON, or an episode directory. ``analyse`` exits 2 when the annotator's output does not conform.
"""
from __future__ import annotations
import argparse, json, sys
from . import __version__
from .annotators import get_annotator, origin, registry
from .loaders import get_loader, loaders
from .schema import FIELD_DOC, validate

def markdown(a: dict) -> str:
    m = a["metrics"]
    out = [f"# {a['room'].get('name')}: {m['posts']} posts, {m['seats']} seats" + (f", {m['span_hours']} h" if m.get("span_hours") else ""),
           "", "| mode | severity | count | confidence | removed by |", "|---|---|---:|---:|---|"]
    order = ["high", "medium", "low", "unknown", "none"]
    for x in sorted(a["modes"], key=lambda x: order.index(x["severity"])):
        out.append(f"| {x['id']} {x['name']} | {x['severity']} | {x['count']} | {x['confidence']} | {x['removed_by']} |")
    out += ["", f"heartbeat share {m['heartbeat_share']:.0%}, asks unanswered {m['asks_unanswered']}/{m['asks']}, "
                f"re-claims {m['re_claims']}/{m['claims']}, open items at end {m['open_items_at_end']}, last post: {m['last_post_kind']}"]
    return "\n".join(out)

def _first_line(doc) -> str:
    lines = (doc or "").strip().splitlines()
    return lines[0] if lines else ""

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="commsfail", description="communication-failure analysis of multi-agent message boards")
    ap.add_argument("--version", action="version", version=f"commsfail {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    an = sub.add_parser("analyse", help="analyse one board and print (or write) an analysis.v1 record")
    an.add_argument("source", help="what the loader accepts; for 'auto': a share link, a shr_ token, share.json, room.ndjson, an episode dir")
    an.add_argument("--loader", default="auto", help="a registered loader (default: auto, the SharedNet formats)")
    an.add_argument("--annotator", default="regex_v1", help="a registered annotator (default: regex_v1)")
    an.add_argument("--markdown", action="store_true", help="print a short table instead of the JSON record")
    an.add_argument("-o", "--out", help="write to this file instead of stdout")
    sub.add_parser("annotators", help="list registered annotators")
    sub.add_parser("loaders", help="list registered loaders")
    sub.add_parser("schema", help="print the analysis.v1 field documentation")
    va = sub.add_parser("validate", help="check an analysis.v1 file"); va.add_argument("file")
    a = ap.parse_args(argv)
    if a.cmd == "annotators":
        for name, cls in sorted(registry().items()):
            print(f"{name:<14} {str(getattr(cls, 'version', '?')):<8} {origin(cls):<28} {_first_line(cls.__doc__)}")
        return 0
    if a.cmd == "loaders":
        for name, fn in sorted(loaders().items()):
            where = "builtin" if fn.__module__.startswith("commsfail.") else fn.__module__
            print(f"{name:<14} {where:<37} {_first_line(fn.__doc__)}")
        return 0
    if a.cmd == "schema":
        print(json.dumps(FIELD_DOC, indent=1)); return 0
    if a.cmd == "validate":
        with open(a.file, encoding="utf-8") as f:
            errs = validate(json.load(f))
        print("\n".join(errs) if errs else "ok"); return 1 if errs else 0
    trace = get_loader(a.loader)(a.source)
    res = get_annotator(a.annotator).annotate(trace)
    errs = validate(res)
    if errs:
        print("annotator output does not conform:\n  " + "\n  ".join(errs), file=sys.stderr); return 2
    text = markdown(res) if a.markdown else json.dumps(res, ensure_ascii=False, indent=1)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"wrote {a.out}")
    else:
        print(text)
    return 0

if __name__ == "__main__":
    sys.exit(main())
