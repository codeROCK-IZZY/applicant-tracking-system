"""Markdown and HTML versions of the evaluation."""

from __future__ import annotations

import html
from typing import Any

from .process import PROCESSES

BANKS = {
    "heldout": "Held-out companies",
    "shifted": "Shifted companies (held back): more bias, less history",
    "tuning": "Tuning companies",
}


def pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def markdown(r: dict[str, Any]) -> str:
    t = r["tuning"]
    out = [
        "# Applicant tracking: evaluation",
        "",
        "Simulated companies hiring: candidates with a true ability nobody sees, interviewers who differ in "
        "leniency, consistency, halo and (for some) bias towards their own group. Quality is the true job "
        "performance of the people hired, in standard deviations; fairness is group B's hire rate over group A's "
        "(below 0.8 fails the four-fifths rule).",
        "",
        f"Chosen on the tuning companies: leniency shrinkage {t['prior']} pseudo-ratings; audit flags a gap over "
        f"{t['min_gap']} with t over {t['min_t']}.",
        "",
    ]
    for b, label in BANKS.items():
        x = r["banks"][b]
        out += [
            f"## {label}: {x['companies']} companies, {x['applicants']:,} applicants",
            "",
            "| Process | Hire performance | Hires in top 10% | Impact ratio (B/A) | Companies below 4/5 |",
            "|---|---:|---:|---:|---:|",
        ]
        for p in PROCESSES:
            a = x["processes"][p]
            out.append(
                f"| {a['label']} | {a['hire_performance']:+.2f} | {pct(a['hires_top_decile'])} | "
                f"{a['impact_ratio']:.2f} | {a['companies_below_four_fifths']} of {x['companies']} |"
            )
        au = x["audit"]
        out += [
            "",
            f"Audit: {au['found']} of {au['biased']} biased interviewers found, {au['false_flags']} false flags "
            f"({pct(au['false_flag_rate'])} of the others). Leniency estimates vs truth: r = "
            f"{x['leniency_correlation']:.2f}.",
            "",
        ]
    out += ["## Tuning", "", "| Leniency shrinkage | Calibrated hire performance |", "|---:|---:|"]
    out += [f"| {p['prior']} | {p['hire_performance']:+.3f} |" for p in t["priors"]]
    out += ["", "| Audit gap | t | Biased found | False flags |", "|---:|---:|---:|---:|"]
    out += [
        f"| {a['min_gap']} | {a['min_t']} | {pct(a['recall'])} | {pct(a['false_flag_rate'])} |" for a in t["audits"]
    ]
    g = r.get("gate")
    if g:
        out += ["", "## Gate (limits written before the held-out run)", ""]
        out += [
            f"- {'PASS' if g['ok'][k] else 'FAIL'} {k}: {v} (limit {g['limits'][k]})" for k, v in g["checks"].items()
        ]
    return "\n".join(out) + "\n"


CSS = """
:root{--bg:#0d1016;--panel:#151b24;--line:#263042;--ink:#e8edf4;--ink2:#97a3b6;--ok:#3ccf8e;--bad:#ff6b6b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 Inter,system-ui,sans-serif}
main{max-width:1180px;margin:0 auto;padding:34px 28px 56px}h1{font-size:28px;margin:0 0 4px}h2{font-size:18px;
margin:28px 0 12px}.sub{color:var(--ink2);margin:0 0 20px}.tiles{display:grid;grid-template-columns:repeat(4,1fr);
gap:12px}.tile{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px}.tile b{
display:block;font-size:26px}.tile span{color:var(--ink2);font-size:13px}table{width:100%;border-collapse:collapse;
background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden;font-size:13.5px}th,td{
padding:8px 12px;border-bottom:1px solid var(--line);text-align:right}th:first-child,td:first-child{text-align:left}
th{color:var(--ink2);font-weight:500;font-size:12px}.good{color:var(--ok);font-weight:600}.bad{color:var(--bad);
font-weight:600}@media(max-width:800px){.tiles{grid-template-columns:1fr 1fr}}
"""


def html_report(r: dict[str, Any]) -> str:
    e = html.escape
    h = r["banks"]["heldout"]["processes"]
    s = r["banks"]["shifted"]["processes"]
    au = r["banks"]["heldout"]["audit"]
    tiles = [
        (
            f"{h['calibrated']['hire_performance'] - h['gut']['hire_performance']:+.2f} SD",
            "better hires with calibrated rubric scores than one interviewer's overall impression (held-out)",
        ),
        (
            f"{h['audited']['impact_ratio']:.2f} vs {h['structured']['impact_ratio']:.2f}",
            "hire-rate ratio B/A: fair process vs plain structured panels (0.8 is the four-fifths line)",
        ),
        (
            f"{au['found']} of {au['biased']}",
            f"biased interviewers found by the audit, {au['false_flags']} false flags",
        ),
        (
            f"{s['audited']['impact_ratio']:.2f}",
            "impact ratio in the shifted companies, where the audit had little history",
        ),
    ]
    out = [
        "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,"
        f"initial-scale=1'><title>Applicant tracking evaluation</title><style>{CSS}</style><main><h1>Applicant "
        "tracking: evaluation</h1><p class='sub'>Simulated companies hiring with interviewers who differ in leniency, "
        "consistency, halo and bias. Settings were chosen on separate tuning companies.</p><div class='tiles'>"
    ]
    out += [f"<div class='tile'><b>{e(v)}</b><span>{e(t)}</span></div>" for v, t in tiles]
    out.append("</div>")
    for b, label in BANKS.items():
        x = r["banks"][b]
        top = max(x["processes"][p]["hire_performance"] for p in PROCESSES)
        out.append(
            f"<h2>{e(label)}: {x['companies']} companies</h2><table><tr><th>Process</th><th>Hire performance</th>"
            "<th>Hires in top 10%</th><th>Impact ratio (B/A)</th><th>Companies below 4/5</th></tr>"
        )
        for p in PROCESSES:
            a = x["processes"][p]
            out.append(
                f"<tr><td>{e(a['label'])}</td><td class='{'good' if a['hire_performance'] == top else ''}'>"
                f"{a['hire_performance']:+.2f}</td><td>{pct(a['hires_top_decile'])}</td><td class='"
                f"{'good' if a['impact_ratio'] >= 0.8 else 'bad'}'>{a['impact_ratio']:.2f}</td><td>"
                f"{a['companies_below_four_fifths']} of {x['companies']}</td></tr>"
            )
        a = x["audit"]
        out.append(
            f"</table><p class='sub' style='margin-top:10px'>Audit: {a['found']} of {a['biased']} biased "
            f"interviewers found, {a['false_flags']} false flags. Leniency estimates vs truth r = "
            f"{x['leniency_correlation']:.2f}.</p>"
        )
    g = r.get("gate")
    if g:
        out.append(
            "<h2>Gate (limits written before the held-out run)</h2><table><tr><th>Check</th><th>Value</th>"
            "<th>Limit</th><th>Result</th></tr>"
        )
        for k, v in g["checks"].items():
            ok = g["ok"][k]
            out.append(
                f"<tr><td>{e(k)}</td><td>{v}</td><td>{g['limits'][k]}</td><td class='{'good' if ok else 'bad'}'>"
                f"{'pass' if ok else 'fail'}</td></tr>"
            )
        out.append("</table>")
    out.append("</main></html>")
    return "".join(out) + "\n"
