"""Command line: screen a résumé blind, the interviewer audit, the console, and the evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ats", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("screen", help="a blind résumé screen (Claude with ANTHROPIC_API_KEY, rules otherwise)")
    s.add_argument("file", help="a text file with the résumé, or - for standard input")
    s.add_argument("--role", default="Backend Engineer")
    sub.add_parser("interviewers", help="leniency and the own-group audit for the demo company")
    sv = sub.add_parser("serve", help="the console with the demo company")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8000)
    ev = sub.add_parser("evaluate", help="hiring processes on held-out and shifted companies")
    ev.add_argument("--out", default="eval/reports")
    ev.add_argument("--gate", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "evaluate":
        from .evaluate import run_all, save

        result = run_all(gate=args.gate)
        save(result, Path(args.out))
        print((Path(args.out) / "report.md").read_text(encoding="utf-8"))
        return 1 if args.gate and not result["gate"]["passed"] else 0
    if args.cmd == "serve":
        import uvicorn

        from .app import demo_app

        uvicorn.run(demo_app(), host=args.host, port=args.port)
        return 0
    if args.cmd == "screen":
        import os

        from .app import evidence_json
        from .screen import Screener, screen_local

        text = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
        evidence = Screener().read(text, args.role) if os.environ.get("ANTHROPIC_API_KEY") else screen_local(text)
        print(json.dumps(evidence_json(evidence), indent=2, ensure_ascii=False))
        return 0
    from .app import demo_console, int_name

    c = demo_console()
    for f in sorted(c.flags, key=lambda f: -f.t):
        mark = "FLAGGED" if f.flagged else ""
        print(
            f"{int_name(f.interviewer):8s} leniency {c.lean.get(f.interviewer, 0.0):+.2f}  own-group gap {f.gap:+.2f}  "
            f"t {f.t:5.1f}  {mark}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
