"""The evaluation: which way of deciding hires picks better people, and which treats both groups fairly?

Three banks of simulated companies, never mixed:

- **tuning** (6 companies): the only place settings are chosen (leniency shrinkage, audit thresholds).
- **held-out** (15 companies): run once the settings and this file were committed.
- **shifted** (8 companies, held back): more interviewers, more of them biased and by more, more spread in leniency,
  and much less history to learn from.

Every process sees the same candidates, interviewers and random draws. Quality is the true job performance of the
people hired (in standard deviations of the applicant pool); fairness is the four-fifths rule: group B's hire rate
divided by group A's. The four-fifths rule works in both directions: the lower rate over the higher below 0.8 is
evidence of adverse impact against either group.
"""

from __future__ import annotations

import json
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from .calibrate import audit, leniency
from .process import LABELS, PROCESSES, four_fifths, history_ratings, run, summary
from .world import SHIFTED, Company, Shape, make_company

BANKS: dict[str, tuple[tuple[int, ...], Shape]] = {
    "tuning": (tuple(range(1, 7)), Shape()),
    "heldout": (tuple(range(101, 116)), Shape()),
    "shifted": (tuple(range(201, 209)), SHIFTED),
}
PRIORS = (0.0, 2.0, 5.0, 10.0, 20.0)
AUDIT_GRID = tuple((gap, t) for gap in (0.2, 0.3, 0.4) for t in (2.0, 2.5, 3.0))
MAX_FALSE_FLAG_RATE = 0.03  # of interviewers without a bias, chosen before tuning

# Written before the held-out and shifted banks were run.
GATE = {
    "heldout_calibrated_over_gut_min": 0.15,  # hire performance, standard deviations
    "heldout_fair_impact_ratio_min": 0.80,
    "heldout_fair_not_worse_than_structured": 0.0,
    "heldout_audit_recall_min": 0.5,
    "heldout_audit_false_flag_rate_max": 0.05,
    "shifted_calibrated_over_gut_min": 0.10,
    "shifted_fair_impact_ratio_min": 0.75,
}


def company_setup(
    seed: int, shape: Shape, prior: float, gap: float, t: float
) -> tuple[Company, dict[int, float], set[int], list[Any]]:
    co = make_company(seed, shape)
    hist = history_ratings(co, seed + 1000)
    lean = leniency(hist, prior)
    flags = audit(hist, {i.id: i.group for i in co.interviewers}, gap, t)
    return co, lean, {f.interviewer for f in flags if f.flagged}, flags


def audit_counts(co: Company, excluded: set[int]) -> dict[str, int]:
    return {
        "interviewers": len(co.interviewers),
        "biased": sum(i.biased for i in co.interviewers),
        "found": sum(i.biased and i.id in excluded for i in co.interviewers),
        "false_flags": sum((not i.biased) and i.id in excluded for i in co.interviewers),
    }


def run_bank(seeds: Sequence[int], shape: Shape, prior: float, gap: float, t: float) -> dict[str, Any]:
    rows: dict[str, list[dict[str, float]]] = {p: [] for p in PROCESSES}
    counts = {"interviewers": 0, "biased": 0, "found": 0, "false_flags": 0}
    lean_corr = []
    for seed in seeds:
        co, lean, excluded, _ = company_setup(seed, shape, prior, gap, t)
        for k, v in audit_counts(co, excluded).items():
            counts[k] += v
        lean_corr.append(
            float(np.corrcoef([lean[i.id] for i in co.interviewers], [i.leniency for i in co.interviewers])[0, 1])
        )
        for p in PROCESSES:
            rows[p].append(summary(run(co, p, seed + 2000, lean, excluded)))
    out: dict[str, Any] = {"companies": len(seeds), "processes": {}}
    for p, rs in rows.items():
        hires = sum(r["hires"] for r in rs)
        rate_a = float(np.average([r["hire_rate_a"] for r in rs]))
        rate_b = float(np.average([r["hire_rate_b"] for r in rs]))
        out["processes"][p] = {
            "label": LABELS[p],
            "hires": hires,
            "hire_performance": float(np.mean([r["hire_performance"] for r in rs])),
            "hires_top_decile": float(np.mean([r["hires_top_decile"] for r in rs])),
            "best_applicant_hired": float(np.mean([r["best_applicant_hired"] for r in rs])),
            "impact_ratio": rate_b / rate_a if rate_a else 0.0,
            "screen_impact_ratio": float(np.mean([r["screen_impact_ratio"] for r in rs])),
            "companies_below_four_fifths": sum(four_fifths(r["impact_ratio"]) < 0.8 for r in rs),
            "share_b_hired": float(np.mean([r["share_b_hired"] for r in rs])),
        }
    unbiased = counts["interviewers"] - counts["biased"]
    out["audit"] = {
        **counts,
        "recall": counts["found"] / max(1, counts["biased"]),
        "false_flag_rate": counts["false_flags"] / max(1, unbiased),
    }
    out["leniency_correlation"] = float(np.mean(lean_corr))
    out["applicants"] = int(sum(shape.applicants * shape.reqs for _ in seeds))
    return out


def tune() -> dict[str, Any]:
    seeds, shape = BANKS["tuning"]
    priors = []
    for prior in PRIORS:
        b = run_bank(seeds, shape, prior, 0.3, 2.5)
        priors.append({"prior": prior, "hire_performance": b["processes"]["calibrated"]["hire_performance"]})
    best_prior = max(priors, key=lambda r: (round(r["hire_performance"], 4), r["prior"]))["prior"]
    audits = []
    for gap, t in AUDIT_GRID:
        found = false = biased = interviewers = 0
        for seed in seeds:
            co, _, excluded, _ = company_setup(seed, shape, best_prior, gap, t)
            c = audit_counts(co, excluded)
            found += c["found"]
            false += c["false_flags"]
            biased += c["biased"]
            interviewers += c["interviewers"]
        audits.append(
            {
                "min_gap": gap,
                "min_t": t,
                "recall": found / max(1, biased),
                "false_flag_rate": false / max(1, interviewers - biased),
            }
        )
    ok = [a for a in audits if a["false_flag_rate"] <= MAX_FALSE_FLAG_RATE] or audits
    best = max(ok, key=lambda a: (a["recall"], -a["false_flag_rate"], a["min_t"], a["min_gap"]))
    return {"priors": priors, "prior": best_prior, "audits": audits, "min_gap": best["min_gap"], "min_t": best["min_t"]}


def run_all(gate: bool = False) -> dict[str, Any]:
    t0 = time.time()
    tuning = tune()
    result: dict[str, Any] = {"tuning": tuning, "banks": {}}
    for name, (seeds, shape) in BANKS.items():
        result["banks"][name] = run_bank(seeds, shape, tuning["prior"], tuning["min_gap"], tuning["min_t"])
    result["seconds"] = round(time.time() - t0, 1)
    if gate:
        result["gate"] = check_gate(result)
    return result


def check_gate(r: dict[str, Any]) -> dict[str, Any]:
    h, s = r["banks"]["heldout"], r["banks"]["shifted"]
    hp, sp = h["processes"], s["processes"]
    checks = {
        "heldout_calibrated_over_gut_min": hp["calibrated"]["hire_performance"] - hp["gut"]["hire_performance"],
        "heldout_fair_impact_ratio_min": four_fifths(hp["audited"]["impact_ratio"]),
        "heldout_fair_not_worse_than_structured": hp["audited"]["hire_performance"]
        - hp["structured"]["hire_performance"],
        "heldout_audit_recall_min": h["audit"]["recall"],
        "heldout_audit_false_flag_rate_max": h["audit"]["false_flag_rate"],
        "shifted_calibrated_over_gut_min": sp["calibrated"]["hire_performance"] - sp["gut"]["hire_performance"],
        "shifted_fair_impact_ratio_min": four_fifths(sp["audited"]["impact_ratio"]),
    }
    passed = {k: (v <= GATE[k] if k.endswith("_max") else v >= GATE[k]) for k, v in checks.items()}
    return {
        "passed": all(passed.values()),
        "checks": {k: round(v, 4) for k, v in checks.items()},
        "ok": passed,
        "limits": GATE,
    }


def save(result: dict[str, Any], out: Path) -> None:
    from .report import html_report, markdown

    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    (out / "report.md").write_text(markdown(result), encoding="utf-8", newline="\n")
    (out / "report.html").write_text(html_report(result), encoding="utf-8", newline="\n")
