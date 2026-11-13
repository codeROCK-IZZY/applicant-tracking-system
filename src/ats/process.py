"""Ways of deciding whom to hire, run on the same candidates, the same interviewers and the same random draws.

- `gut`: one interviewer per candidate gives an overall impression; the highest are hired.
- `discussion`: a panel of three, then an open debrief where everyone moves halfway towards the first person to
  speak (anchoring), as unstructured debriefs tend to.
- `structured`: a panel of three scores each competency on a rubric, independently, before any discussion; the
  scores are weighted by the role's competency weights and averaged.
- `calibrated`: structured, with each interviewer's leniency (learned from earlier panels) taken out first.
- `audited`: calibrated, the school hidden from the résumé screen and from the interview packet, and interviewers
  flagged by the audit for scoring their own group higher kept off panels until reviewed.

Every process screens the same applicants down to the same number of interviews. Results are measured against the
candidates' true job performance, which the processes never see.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from .world import WEIGHTS, Candidate, Company, Interviewer, Req, rate, resume_signal

PROCESSES = ("gut", "discussion", "structured", "calibrated", "audited")
LABELS = {
    "gut": "One interviewer's overall impression",
    "discussion": "Panel of three, open debrief",
    "structured": "Panel of three, independent rubric scores",
    "calibrated": "Rubric scores, interviewer leniency taken out",
    "audited": "Calibrated + school hidden + flagged interviewers off panels",
}
PANEL = 3


@dataclass
class Rating:
    req: int
    candidate: int
    group: str
    interviewer: int
    score: float  # weighted rubric score


@dataclass
class Outcome:
    hired: list[Candidate] = field(default_factory=list)
    interviewed: list[Candidate] = field(default_factory=list)
    applicants: list[Candidate] = field(default_factory=list)
    ratings: list[Rating] = field(default_factory=list)


def weighted(scores: np.ndarray) -> float:
    return float(WEIGHTS @ scores / WEIGHTS.sum())


def history_ratings(company: Company, seed: int) -> list[Rating]:
    """Earlier requisitions run with structured panels (the interviewer records calibration and the audit learn from)."""
    g = np.random.default_rng(seed)
    out = []
    for req in company.reqs:
        if not req.history:
            continue
        screened = sorted(req.candidates, key=lambda c: -resume_signal(c, g, blind=False))[: company.shape.interviewed]
        for c in screened:
            for k in g.choice(len(company.interviewers), PANEL, replace=False):
                i = company.interviewers[int(k)]
                out.append(Rating(req.id, c.id, c.group, i.id, weighted(rate(i, c, g))))
    return out


def run_req(
    req: Req, company: Company, process: str, g: np.random.Generator, leniency: dict[int, float], excluded: set[int]
) -> Outcome:
    shape = company.shape
    blind = process == "audited"
    screened = sorted(req.candidates, key=lambda c: -resume_signal(c, g, blind))[: shape.interviewed]
    pool = [i for i in company.interviewers if process != "audited" or i.id not in excluded]
    if len(pool) < PANEL:
        pool = list(company.interviewers)
    out = Outcome(applicants=list(req.candidates), interviewed=screened)
    final: dict[int, float] = {}
    for c in screened:
        size = 1 if process == "gut" else PANEL
        panel: list[Interviewer] = [pool[int(k)] for k in g.choice(len(pool), size, replace=False)]
        scores = [weighted(rate(i, c, g, see_school=not blind)) for i in panel]
        for i, s in zip(panel, scores, strict=True):
            out.ratings.append(Rating(req.id, c.id, c.group, i.id, s))
        if process == "discussion":
            first = scores[0]
            final[c.id] = float(np.mean([0.5 * s + 0.5 * first for s in scores]))
        elif process in ("calibrated", "audited"):
            final[c.id] = float(np.mean([s - leniency.get(i.id, 0.0) for i, s in zip(panel, scores, strict=True)]))
        else:
            final[c.id] = float(np.mean(scores))
    out.hired = sorted(screened, key=lambda c: -final[c.id])[: shape.hires]
    return out


def run(company: Company, process: str, seed: int, leniency: dict[int, float], excluded: set[int]) -> list[Outcome]:
    """All the measured requisitions. The same seed gives every process the same screen and panel draws' order."""
    g = np.random.default_rng(seed)
    return [run_req(r, company, process, g, leniency, excluded) for r in company.reqs if not r.history]


def four_fifths(ratio: float) -> float:
    """The four-fifths rule in both directions: the lower group's rate over the higher group's."""
    if ratio <= 0:
        return 0.0
    return min(ratio, 1 / ratio)


def summary(outcomes: Sequence[Outcome]) -> dict[str, float]:
    hired = [c for o in outcomes for c in o.hired]
    apps = [c for o in outcomes for c in o.applicants]
    inter = [c for o in outcomes for c in o.interviewed]
    perf = np.array([c.performance for c in hired])
    cut = float(np.quantile([c.performance for c in apps], 0.9))

    def rate_of(group: str, chosen: Sequence[Candidate], base: Sequence[Candidate]) -> float:
        n = sum(c.group == group for c in base)
        return sum(c.group == group for c in chosen) / n if n else 0.0

    ra, rb = rate_of("A", hired, apps), rate_of("B", hired, apps)
    sa, sb = rate_of("A", inter, apps), rate_of("B", inter, apps)
    best = [max(o.applicants, key=lambda c: c.performance) for o in outcomes]
    return {
        "reqs": len(outcomes),
        "hires": len(hired),
        "hire_performance": float(perf.mean()),
        "hires_top_decile": float(np.mean(perf >= cut)),
        "best_applicant_hired": float(np.mean([b in o.hired for b, o in zip(best, outcomes, strict=True)])),
        "hire_rate_a": ra,
        "hire_rate_b": rb,
        "impact_ratio": rb / ra if ra else 0.0,
        "screen_impact_ratio": sb / sa if sa else 0.0,
        "hired_a": float(sum(c.group == "A" for c in hired)),
        "hired_b": float(sum(c.group == "B" for c in hired)),
        "share_b_hired": float(np.mean([c.group == "B" for c in hired])),
        "share_b_applied": float(np.mean([c.group == "B" for c in apps])),
    }
