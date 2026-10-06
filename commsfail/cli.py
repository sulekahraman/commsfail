"""commsfail command line.

    commsfail analyse <src> [--annotator regex_v1] [--source sharednet] [--markdown] [-o out.json]
    commsfail trace <src> [--source sharednet] [--full]   what a source holds, before you annotate it
    commsfail annotators                                  the registered annotators, built in and plugins
    commsfail sources                                     the registered sources
    commsfail schema <annotator>                          an annotator's output schema
    commsfail validate <record.json>                      check a record; exit 1 if it does not conform
    commsfail new <name>                                  start a new annotator folder (run it in the repository root)

With the default source, <src> is a goal-run record folder, a room.ndjson, a table export, a saved share JSON,
or a share link. ``analyse`` writes a record (the annotator's output in an envelope) and exits 2 when the
output does not conform to the annotator's own schema.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from . import __version__
from .annotators import get_annotator, make_record, origin, registry, schema_of, validate_output, validate_record
from .annotators.base import NAME_RE
from .sources import DEFAULT, get_source, sources
from .sources.sharednet import summary

def _first_line(doc) -> str:
    lines = (doc or "").strip().splitlines()
    return lines[0] if lines else ""

def scaffold(name: str, root: Path) -> list[Path]:
    """Copy the template annotator to commsfail/annotators/<name>/ and tests/annotators/test_<name>.py."""
    if not NAME_RE.match(name):
        raise SystemExit("the name must be 2 to 41 characters: lowercase letters, digits and _, starting with a letter")
    pkg = root / "commsfail" / "annotators"
    if not pkg.is_dir():
        raise SystemExit(f"{pkg} not found: run `commsfail new` in the root of a commsfail checkout")
    dest, test = pkg / name, root / "tests" / "annotators" / f"test_{name}.py"
    for p in (dest, test):
        if p.exists():
            raise SystemExit(f"{p} exists already")
    cls = "".join(w[:1].upper() + w[1:] for w in name.split("_"))
    tpl = Path(__file__).resolve().parent / "annotators" / "_template"
    fill = lambda s: s.replace("TemplateName", cls).replace("template_name", name)
    dest.mkdir(parents=True)
    test.parent.mkdir(parents=True, exist_ok=True)
    made = []
    for src, dst in [(tpl / "__init__.py", dest / "__init__.py"), (tpl / "schema.json", dest / "schema.json"),
                     (tpl / "README.md", dest / "README.md"), (tpl / "test_template.py.txt", test)]:
        dst.write_text(fill(src.read_text(encoding="utf-8")), encoding="utf-8")
        made.append(dst)
    return made

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="commsfail", description="communication-failure analysis of multi-agent message boards")
    ap.add_argument("--version", action="version", version=f"commsfail {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    an = sub.add_parser("analyse", help="annotate one board and print (or write) the record")
    an.add_argument("src", help="for the sharednet source: a record folder, room.ndjson, share.json, or a share link")
    an.add_argument("--annotator", default="regex_v1", help="a registered annotator (default: regex_v1)")
    an.add_argument("--source", default=DEFAULT, help=f"a registered source (default: {DEFAULT})")
    an.add_argument("--markdown", action="store_true", help="print the annotator's short view instead of the record")
    an.add_argument("-o", "--out", help="write to this file instead of stdout")
    tr = sub.add_parser("trace", help="show what a source holds")
    tr.add_argument("src"); tr.add_argument("--source", default=DEFAULT)
    tr.add_argument("--full", action="store_true", help="print the whole Trace as JSON, not a summary")
    sub.add_parser("annotators", help="list registered annotators")
    sub.add_parser("sources", help="list registered sources")
    sc = sub.add_parser("schema", help="print an annotator's output schema"); sc.add_argument("annotator")
    va = sub.add_parser("validate", help="check a record file"); va.add_argument("file")
    nw = sub.add_parser("new", help="start a new annotator folder from the template")
    nw.add_argument("name"); nw.add_argument("--root", default=".", help="the repository root (default: .)")
    a = ap.parse_args(argv)

    if a.cmd == "annotators":
        for name, cls in sorted(registry().items()):
            print(f"{name:<16} {str(getattr(cls, 'version', '?')):<8} {origin(cls):<24} {schema_of(cls).get('$id', '?'):<30} {_first_line(cls.__doc__)}")
        return 0
    if a.cmd == "sources":
        for name, fn in sorted(sources().items()):
            where = "builtin" if fn.__module__.startswith("commsfail.") else fn.__module__
            print(f"{name:<14} {where:<24} {_first_line(fn.__doc__)}")
        return 0
    if a.cmd == "schema":
        print(json.dumps(schema_of(get_annotator(a.annotator)), indent=2)); return 0
    if a.cmd == "validate":
        with open(a.file, encoding="utf-8") as f:
            errs = validate_record(json.load(f))
        print("\n".join(errs) if errs else "ok"); return 1 if errs else 0
    if a.cmd == "new":
        made = scaffold(a.name, Path(a.root))
        print("made:\n  " + "\n  ".join(str(p) for p in made))
        print(f"next: write your method in {made[0]}, describe its output in {made[1]}, then run pytest")
        return 0

    trace = get_source(a.source)(a.src)
    if a.cmd == "trace":
        print(json.dumps(trace.to_dict() if a.full else summary(trace), ensure_ascii=False, indent=1)); return 0
    ann = get_annotator(a.annotator)
    output = ann.annotate(trace)
    errs = validate_output(ann, output)
    if errs:
        print(f"{ann.name} output does not conform to its schema:\n  " + "\n  ".join(errs[:20]), file=sys.stderr); return 2
    if a.markdown:
        if not callable(getattr(ann, "markdown", None)):
            print(f"{ann.name} has no markdown view; leave out --markdown", file=sys.stderr); return 1
        text = ann.markdown(output)
    else:
        text = json.dumps(make_record(ann, trace, output), ensure_ascii=False, indent=1)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"wrote {a.out}")
    else:
        print(text)
    return 0

if __name__ == "__main__":
    sys.exit(main())
