"""The hiring team's console: open requisitions, each shortlist with its calibrated panel scores, the interviewer
calibration and audit, the four-fifths check by stage, and the blind résumé screen."""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .calibrate import Flag, audit, leniency
from .process import LABELS, Outcome, four_fifths, history_ratings, run, summary
from .screen import Evidence, Screener, screen_local
from .world import COMPETENCIES, Company, Shape, make_company

e = html.escape
SEED = 7
PRIOR, MIN_GAP, MIN_T = 5.0, 0.4, 2.0  # chosen on the tuning companies (see the evaluation report)
ROLES = [
    "Backend Engineer",
    "Data Analyst",
    "Product Designer",
    "Site Reliability Engineer",
    "Customer Success Lead",
    "Frontend Engineer",
    "Finance Associate",
    "QA Engineer",
    "Sales Engineer",
    "People Partner",
]
FIRST = [
    "Alex",
    "Sam",
    "Jordan",
    "Taylor",
    "Riley",
    "Morgan",
    "Casey",
    "Jamie",
    "Avery",
    "Quinn",
    "Rowan",
    "Skyler",
    "Dana",
    "Emerson",
    "Hayden",
    "Kai",
    "Logan",
    "Parker",
    "Reese",
    "Sasha",
]
LAST = [
    "Abbott",
    "Banerjee",
    "Castro",
    "Dimitrov",
    "Eze",
    "Fischer",
    "Garcia",
    "Hughes",
    "Ito",
    "Jensen",
    "Kowalski",
    "Lindqvist",
    "Moreau",
    "Nakamura",
    "Osei",
    "Petrov",
    "Quinn",
    "Rahman",
    "Santos",
    "Tanaka",
]
INTERVIEWERS = [
    "Ada",
    "Bram",
    "Chidi",
    "Dev",
    "Elif",
    "Farah",
    "Goran",
    "Hana",
    "Ivo",
    "Joon",
    "Kemi",
    "Lars",
    "Mira",
    "Nils",
    "Oona",
    "Pavel",
    "Rhea",
    "Soren",
    "Tomas",
    "Uma",
]
SAMPLE = """Jordan Example
jordan@example.com  +44 7700 900123
Experience
Backend engineer, 2021-2025. Designed a Python service and reduced p95 latency by 40% after tracing the root cause.
Mentored two junior engineers and presented the design to stakeholders across three teams.
Education
BSc Computer Science, Famous University, 2020
Skills
Python, SQL, Kubernetes"""

CSS = """
:root{--bg:#0d1117;--panel:#151b24;--line:#263041;--ink:#e8edf4;--ink2:#97a3b6;--ok:#3ccf8e;--bad:#ff6b6b;--mid:#f5b54a;
--acc:#7aa2ff}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 Inter,system-ui,
sans-serif}a{color:inherit}header{padding:14px 26px;border-bottom:1px solid var(--line);display:flex;gap:18px;
align-items:baseline;flex-wrap:wrap}header b{font-size:17px}header nav a{color:var(--ink2);text-decoration:none;
margin-right:14px}main{padding:20px 26px 48px;max-width:1260px;margin:0 auto}.grid{display:grid;
grid-template-columns:repeat(4,1fr);gap:12px}.card{background:var(--panel);border:1px solid var(--line);
border-radius:12px;padding:14px 16px}.card b{display:block;font-size:24px}.muted{color:var(--ink2)}table{width:100%;
border-collapse:collapse;background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden}
th,td{padding:8px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{color:var(--ink2);
font-weight:500;font-size:12px}.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.b{display:inline-block;padding:1px 9px;border-radius:99px;font-size:11.5px;font-weight:600;white-space:nowrap}
.ok{background:#3ccf8e22;color:var(--ok)}.warn{background:#f5b54a22;color:var(--mid)}.bad{background:#ff6b6b22;
color:var(--bad)}.info{background:#7aa2ff22;color:var(--acc)}h1{font-size:22px;margin:0 0 4px}h2{font-size:13px;
color:var(--ink2);text-transform:uppercase;letter-spacing:.05em;margin:24px 0 8px}textarea{width:100%;min-height:200px;
background:#0f141c;color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:8px 10px;font:inherit}
button{background:var(--acc);color:#0b1020;border:0;border-radius:6px;padding:8px 14px;font:inherit;font-weight:600;
cursor:pointer}pre{white-space:pre-wrap;background:#0f141c;border:1px solid var(--line);border-radius:8px;padding:12px}
@media(max-width:900px){.grid{grid-template-columns:1fr 1fr}}
"""


def _page(title: str, body: str) -> str:
    return (
        "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,"
        f"initial-scale=1'><title>{e(title)}</title><style>{CSS}</style><header><b>Fairhire ATS</b><nav>"
        "<a href='/'>Requisitions</a><a href='/interviewers'>Interviewers</a><a href='/fairness'>Four-fifths check</a>"
        "<a href='/screen'>Blind screen</a></nav><span class='muted'>demo company, this quarter</span></header>"
        f"<main>{body}</main></html>"
    )


def cand_name(cid: int) -> str:
    return f"{FIRST[cid % len(FIRST)]} {LAST[(cid * 7 + cid // len(FIRST)) % len(LAST)]}"


def int_name(iid: int) -> str:
    return INTERVIEWERS[iid % len(INTERVIEWERS)]


@dataclass
class Console:
    company: Company
    lean: dict[int, float]
    flags: list[Flag]
    outcomes: list[Outcome]
    compare: dict[str, dict[str, float]]
    screener: Screener | None = None

    @property
    def excluded(self) -> set[int]:
        return {f.interviewer for f in self.flags if f.flagged}


def demo_console(screener: Screener | None = None) -> Console:
    co = make_company(SEED, Shape())
    hist = history_ratings(co, SEED + 1000)
    lean = leniency(hist, PRIOR)
    flags = audit(hist, {i.id: i.group for i in co.interviewers}, MIN_GAP, MIN_T)
    excluded = {f.interviewer for f in flags if f.flagged}
    outcomes = run(co, "audited", SEED + 2000, lean, excluded)
    compare = {p: summary(run(co, p, SEED + 2000, lean, excluded)) for p in ("gut", "structured", "audited")}
    return Console(co, lean, flags, outcomes, compare, screener)


class ScreenIn(BaseModel):
    resume: str
    role: str = "Backend Engineer"


def evidence_json(ev: Evidence) -> dict[str, Any]:
    return {"levels": ev.levels, "quotes": ev.quotes, "source": ev.source, "removed": ev.removed, "dropped": ev.dropped}


def create_app(c: Console) -> FastAPI:
    app = FastAPI(title="Applicant tracking")

    def final_scores(o: Outcome) -> dict[int, float]:
        by: dict[int, list[float]] = {}
        for r in o.ratings:
            by.setdefault(r.candidate, []).append(r.score - c.lean.get(r.interviewer, 0.0))
        return {k: sum(v) / len(v) for k, v in by.items()}

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {"status": "ok", "requisitions": len(c.outcomes), "claude": c.screener is not None}

    @app.get("/api/reqs")
    def api_reqs() -> list[dict[str, Any]]:
        return [
            {
                "id": i,
                "role": ROLES[i % len(ROLES)],
                "applicants": len(o.applicants),
                "interviewed": len(o.interviewed),
                "hired": [cand_name(x.id) for x in o.hired],
            }
            for i, o in enumerate(c.outcomes)
        ]

    @app.get("/api/interviewers")
    def api_interviewers() -> list[dict[str, Any]]:
        return [
            {
                "interviewer": int_name(f.interviewer),
                "leniency": round(c.lean.get(f.interviewer, 0.0), 3),
                "gap": f.gap,
                "t": f.t,
                "n_own": f.n_own,
                "n_other": f.n_other,
                "flagged": f.flagged,
            }
            for f in c.flags
        ]

    @app.post("/api/screen")
    def api_screen(body: ScreenIn) -> dict[str, Any]:
        if not body.resume.strip():
            raise HTTPException(422, "paste a résumé")
        ev = c.screener.read(body.resume, body.role) if c.screener else screen_local(body.resume)
        return evidence_json(ev)

    @app.get("/", response_class=HTMLResponse)
    def reqs() -> str:
        rows = []
        for i, o in enumerate(c.outcomes):
            rows.append(
                f"<tr><td><a href='/reqs/{i}'>{e(ROLES[i % len(ROLES)])}</a><div class='muted'>REQ-{100 + i}</div>"
                f"</td><td class='num'>{len(o.applicants)}</td><td class='num'>{len(o.interviewed)}</td><td>"
                + ", ".join(e(cand_name(x.id)) for x in o.hired)
                + "</td></tr>"
            )
        a = c.compare["audited"]
        body = (
            "<h1>Requisitions</h1><p class='muted'>Each shortlist was interviewed by a panel of three scoring a rubric "
            "independently, with each interviewer's leniency taken out. Schools were hidden from the screen and the "
            "interview packet, and interviewers flagged by the audit sat out.</p><div class='grid'>"
            f"<div class='card'><b>{len(c.outcomes)}</b><span class='muted'>requisitions this quarter</span></div>"
            f"<div class='card'><b>{sum(len(o.hired) for o in c.outcomes)}</b><span class='muted'>hires</span></div>"
            f"<div class='card'><b>{four_fifths(a['impact_ratio']):.2f}</b><span class='muted'>lower group's hire "
            "rate over the higher's (four-fifths line 0.80)</span></div>"
            f"<div class='card'><b>{len(c.excluded)}</b><span class='muted'>interviewers flagged for review</span></div>"
            "</div><h2>Open and filled</h2><table><tr><th>Role</th><th class='num'>Applicants</th><th class='num'>"
            "Interviewed</th><th>Hired</th></tr>" + "".join(rows) + "</table>"
        )
        return _page("Requisitions", body)

    @app.get("/reqs/{rid}", response_class=HTMLResponse)
    def req(rid: int) -> str:
        if not 0 <= rid < len(c.outcomes):
            raise HTTPException(404, "no such requisition")
        o = c.outcomes[rid]
        final = final_scores(o)
        hired = {x.id for x in o.hired}
        rows = []
        for rank, cand in enumerate(sorted(o.interviewed, key=lambda x: -final[x.id]), 1):
            panel = [r for r in o.ratings if r.candidate == cand.id]
            cells = "".join(
                f"<div>{e(int_name(r.interviewer))}: {r.score:.2f} <span class='muted'>"
                f"({-c.lean.get(r.interviewer, 0.0):+.2f})</span></div>"
                for r in panel
            )
            badge = "<span class='b ok'>offer</span>" if cand.id in hired else ""
            rows.append(
                f"<tr><td class='num'>{rank}</td><td>{e(cand_name(cand.id))} {badge}</td><td>{cells}</td>"
                f"<td class='num'><b>{final[cand.id]:.2f}</b></td></tr>"
            )
        body = (
            f"<h1>{e(ROLES[rid % len(ROLES)])} <span class='muted'>REQ-{100 + rid}</span></h1><p class='muted'>"
            f"{len(o.applicants)} applicants, {len(o.interviewed)} interviewed. Each score is the panel member's "
            "rubric score weighted by the role's competencies; in brackets, the leniency adjustment learned from "
            "their earlier panels.</p><table><tr><th class='num'>Rank</th><th>Candidate</th><th>Panel (raw, "
            "adjustment)</th><th class='num'>Calibrated</th></tr>" + "".join(rows) + "</table>"
            f"<p class='muted'>Competencies: {e(', '.join(COMPETENCIES))}.</p>"
        )
        return _page(ROLES[rid % len(ROLES)], body)

    @app.get("/interviewers", response_class=HTMLResponse)
    def interviewers() -> str:
        rows = []
        for f in sorted(c.flags, key=lambda f: -f.t):
            st = (
                "<span class='b bad'>flagged for review</span>"
                if f.flagged
                else "<span class='b warn'>watch</span>"
                if f.t > 1.5
                else "<span class='b ok'>no signal</span>"
            )
            rows.append(
                f"<tr><td>{e(int_name(f.interviewer))}</td><td class='num'>{c.lean.get(f.interviewer, 0.0):+.2f}</td>"
                f"<td class='num'>{f.gap:+.2f}</td><td class='num'>{f.t:.1f}</td><td class='num'>{f.n_own} / "
                f"{f.n_other}</td><td>{st}</td></tr>"
            )
        body = (
            "<h1>Interviewers</h1><p class='muted'>Learned from last quarter's panels. <b>Leniency</b>: how much "
            "higher or lower than co-panelists they score everyone, taken out of their scores. <b>Own-group gap</b>: "
            "how much more they score candidates of their own group than their co-panelists do, compared with "
            "candidates of other groups. A clear gap flags them for a person to review and keeps them off panels "
            "meanwhile; it never changes any candidate's score.</p><table><tr><th>Interviewer</th><th class='num'>"
            "Leniency</th><th class='num'>Own-group gap</th><th class='num'>t</th><th class='num'>Scores (own / "
            "other)</th><th></th></tr>" + "".join(rows) + "</table>"
        )
        return _page("Interviewers", body)

    @app.get("/fairness", response_class=HTMLResponse)
    def fairness() -> str:
        rows = []
        for p, s in c.compare.items():
            for stage, key in (("screen", "screen_impact_ratio"), ("hire", "impact_ratio")):
                v = s[key]
                ok = four_fifths(v) >= 0.8
                who = "" if ok else (" (group B lower)" if v < 1 else " (group A lower)")
                counts = f"{int(s['hired_a'])} A, {int(s['hired_b'])} B hired" if stage == "hire" else ""
                rows.append(
                    f"<tr><td>{e(LABELS[p])}</td><td>{stage}</td><td class='num'>{v:.2f}</td><td>"
                    f"<span class='b {'ok' if ok else 'bad'}'>{'passes' if ok else 'below 4/5' + who}</span></td>"
                    f"<td class='muted'>{counts}</td></tr>"
                )
        body = (
            "<h1>Four-fifths check</h1><p class='muted'>Selection rate of group B divided by that of group A at each "
            "stage, this quarter. The rule works in both directions: the lower group's rate below 0.80 of the "
            "higher group's is the usual evidence of adverse impact. With a few dozen hires one quarter's ratio is "
            "noisy; the evaluation pools many companies. Group is collected voluntarily, kept apart from "
            "applications and only ever shown in aggregate. The same applicants are shown through two other "
            "processes for comparison.</p><table><tr><th>Process</th><th>Stage</th><th class='num'>Ratio B/A</th>"
            "<th></th><th></th></tr>" + "".join(rows) + "</table>"
        )
        return _page("Four-fifths check", body)

    def screen_page(text: str, ev: Evidence, note: str) -> str:
        rows = "".join(
            f"<tr><td>{e(k)}</td><td class='num'>{v if v is not None else '–'}</td><td class='muted'>"
            f"{e(ev.quotes.get(k) or '')}</td></tr>"
            for k, v in ev.levels.items()
        )
        dropped = "".join(f"<li>{e(d)}</li>" for d in ev.dropped)
        body = (
            f"<h1>Blind résumé screen</h1><p class='muted'>{e(note)} Removed before reading: "
            f"{e(', '.join(ev.removed) or 'nothing')}.</p><form method='post' action='/screen'><textarea name='resume'>"
            f"{e(text)}</textarea><p><button>Screen</button></p></form><h2>Evidence by competency</h2><table><tr>"
            "<th>Competency</th><th class='num'>Level</th><th>From the résumé</th></tr>"
            + rows
            + "</table>"
            + (f"<ul class='muted'>{dropped}</ul>" if dropped else "")
            + "<p class='muted'>Levels are evidence for a person to read, never an automatic rejection.</p>"
        )
        return _page("Blind screen", body)

    @app.get("/screen", response_class=HTMLResponse)
    def screen_form() -> str:
        return screen_page(SAMPLE, screen_local(SAMPLE), "Example, read with keyword rules.")

    @app.post("/screen", response_class=HTMLResponse)
    def screen_post(resume: str = Form("")) -> str:
        if not resume.strip():
            raise HTTPException(422, "paste a résumé")
        if c.screener is not None:
            return screen_page(resume, c.screener.read(resume, "Backend Engineer"), "Read with Claude.")
        return screen_page(resume, screen_local(resume), "Read with keyword rules (no API key set).")

    return app


def demo_app() -> FastAPI:
    import os

    return create_app(demo_console(Screener() if os.environ.get("ANTHROPIC_API_KEY") else None))


__all__ = ["Console", "create_app", "demo_app", "demo_console"]
