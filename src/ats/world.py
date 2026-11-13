"""Simulated companies hiring: candidates with a true ability nobody can see, and interviewers who see it imperfectly.

Each candidate has a true level in four competencies, drawn the same way for every group, and a job performance
that follows from them. Two groups (A and B) differ only in access: group A candidates more often went to a
well-known school, which says nothing about ability here.

Interviewers differ the way real ones do:

- **leniency**: some score everyone higher or lower;
- **noise**: some are much less consistent than others;
- **halo**: one overall impression of the candidate leaks into every competency they score;
- **affinity**: some score candidates from their own group higher (a hidden bias the audit should find);
- **prestige**: some give credit for a well-known school.

The résumé screen sees a noisy signal of ability, plus the school unless the screen is blind.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

COMPETENCIES = ("problem solving", "technical depth", "communication", "collaboration")
WEIGHTS = np.array([0.35, 0.3, 0.2, 0.15])  # how much each competency drives job performance


@dataclass(frozen=True)
class Shape:
    """What kind of company: how its interviewers behave and how much history there is."""

    interviewers: int = 14
    share_group_a_interviewers: float = 0.75
    biased_share: float = 0.25  # interviewers with an affinity bias
    affinity: float = 0.6  # size of that bias, in ability standard deviations
    prestige_bias: float = 0.25
    leniency_sd: float = 0.6
    reqs: int = 30  # requisitions in the period measured
    history_reqs: int = 30  # earlier requisitions, used to calibrate interviewers
    applicants: int = 60
    interviewed: int = 15
    hires: int = 2
    share_group_b: float = 0.4


SHIFTED = Shape(
    interviewers=20, share_group_a_interviewers=0.85, biased_share=0.35, affinity=0.8, leniency_sd=0.9, history_reqs=12
)


@dataclass
class Candidate:
    id: int
    group: str
    prestige: bool
    ability: np.ndarray  # one value per competency
    performance: float


@dataclass
class Interviewer:
    id: int
    group: str
    leniency: float
    noise: float
    halo: float
    affinity: float  # added when the candidate shares the interviewer's group
    prestige: float

    @property
    def biased(self) -> bool:
        return self.affinity > 0.2


@dataclass
class Req:
    id: int
    candidates: list[Candidate]
    history: bool = False


@dataclass
class Company:
    seed: int
    shape: Shape
    interviewers: list[Interviewer]
    reqs: list[Req] = field(default_factory=list)


def make_company(seed: int, shape: Shape = Shape()) -> Company:
    g = np.random.default_rng(seed)
    people = []
    for i in range(shape.interviewers):
        group = "A" if g.random() < shape.share_group_a_interviewers else "B"
        biased = g.random() < shape.biased_share
        people.append(
            Interviewer(
                i,
                group,
                leniency=float(g.normal(0, shape.leniency_sd)),
                noise=float(g.uniform(0.4, 1.1)),
                halo=float(g.uniform(0.2, 0.7)),
                affinity=float(shape.affinity * g.uniform(0.7, 1.3)) if biased else 0.0,
                prestige=float(shape.prestige_bias * g.uniform(0, 2)),
            )
        )
    c = Company(seed, shape, people)
    nid = 0
    for r in range(shape.history_reqs + shape.reqs):
        cands = []
        for _ in range(shape.applicants):
            group = "B" if g.random() < shape.share_group_b else "A"
            prestige = bool(g.random() < (0.5 if group == "A" else 0.2))
            ability = g.normal(0, 1, len(COMPETENCIES))
            perf = float(WEIGHTS @ ability + g.normal(0, 0.3))
            cands.append(Candidate(nid, group, prestige, ability, perf))
            nid += 1
        c.reqs.append(Req(r, cands, history=r < shape.history_reqs))
    return c


def resume_signal(c: Candidate, g: np.random.Generator, blind: bool) -> float:
    """What a screener reads into a résumé: ability seen through noise, plus the school unless hidden."""
    return float(WEIGHTS @ c.ability / WEIGHTS.sum() + g.normal(0, 0.9) + (0.0 if blind else 0.5 * c.prestige))


def rate(i: Interviewer, c: Candidate, g: np.random.Generator, see_school: bool = True) -> np.ndarray:
    """One interviewer's scores for one candidate, per competency, on a 1-5 style scale centred on 3.

    `see_school=False` is an interview packet without the education section: the interviewer can't credit it.
    """
    impression = float(WEIGHTS @ c.ability / WEIGHTS.sum()) + float(g.normal(0, i.noise))
    school = i.prestige if c.prestige and see_school else 0.0
    bias = i.leniency + (i.affinity if c.group == i.group else 0.0) + school
    own = c.ability + g.normal(0, i.noise, len(COMPETENCIES))
    raw = (1 - i.halo) * own + i.halo * impression + bias
    return np.asarray(3 + 0.8 * raw, dtype=float)
