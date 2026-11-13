"""Learning about interviewers from their past panels: how lenient each one is, and whether one scores their own
group higher than their co-panelists do.

**Leniency.** Each past score is modelled as candidate level + interviewer leniency + noise, fitted by alternating
least squares over all panels. Leniency is shrunk towards zero by `prior` pseudo-ratings, so an interviewer with few
panels is barely adjusted. The same adjustment applies to every candidate an interviewer sees, whatever their group.

**Affinity audit.** For each interviewer, every past score is compared with the mean of the co-panelists' scores for
the same candidate. If the interviewer's gap is larger for candidates of their own group than for others, by more
than `min_gap` and with a t statistic above `min_t` over at least `min_n` scores of each kind, they are flagged for a
person to review. Flags change who sits on panels; they never change any candidate's score (ADR 2).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .process import Rating


def leniency(ratings: Sequence[Rating], prior: float = 5.0, rounds: int = 20) -> dict[int, float]:
    by_cand: dict[tuple[int, int], list[Rating]] = defaultdict(list)
    for r in ratings:
        by_cand[(r.req, r.candidate)].append(r)
    by_int: dict[int, list[Rating]] = defaultdict(list)
    for r in ratings:
        by_int[r.interviewer].append(r)
    lean = dict.fromkeys(by_int, 0.0)
    level: dict[tuple[int, int], float] = {}
    for _ in range(rounds):
        for k, rs in by_cand.items():
            level[k] = float(np.mean([r.score - lean[r.interviewer] for r in rs]))
        for i, rs in by_int.items():
            resid = [r.score - level[(r.req, r.candidate)] for r in rs]
            lean[i] = float(np.sum(resid) / (len(resid) + prior))
        mean = float(np.mean(list(lean.values())))
        lean = {i: v - mean for i, v in lean.items()}
    return lean


@dataclass
class Flag:
    interviewer: int
    gap: float  # own-group minus other-group, relative to co-panelists
    t: float
    n_own: int
    n_other: int
    flagged: bool


def audit(
    ratings: Sequence[Rating], groups: dict[int, str], min_gap: float = 0.3, min_t: float = 2.5, min_n: int = 8
) -> list[Flag]:
    by_cand: dict[tuple[int, int], list[Rating]] = defaultdict(list)
    for r in ratings:
        by_cand[(r.req, r.candidate)].append(r)
    own: dict[int, list[float]] = defaultdict(list)
    other: dict[int, list[float]] = defaultdict(list)
    for rs in by_cand.values():
        if len(rs) < 2:
            continue
        for r in rs:
            peers = float(np.mean([p.score for p in rs if p is not r]))
            (own if r.group == groups[r.interviewer] else other)[r.interviewer].append(r.score - peers)
    out = []
    for i in sorted(groups):
        a, b = np.array(own.get(i, [])), np.array(other.get(i, []))
        if len(a) < 2 or len(b) < 2:
            out.append(Flag(i, 0.0, 0.0, len(a), len(b), False))
            continue
        gap = float(a.mean() - b.mean())
        se = float(np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))) or 1e-9
        t = gap / se
        ok = len(a) >= min_n and len(b) >= min_n and gap > min_gap and t > min_t
        out.append(Flag(i, round(gap, 3), round(t, 2), len(a), len(b), ok))
    return out
