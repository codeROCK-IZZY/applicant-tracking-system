"""The hiring world, the processes, interviewer calibration and the audit."""

from __future__ import annotations

import dataclasses

import numpy as np

from ats.calibrate import audit, leniency
from ats.process import PROCESSES, Rating, history_ratings, run, summary
from ats.world import SHIFTED, Interviewer, Shape, make_company, rate, resume_signal

SMALL = Shape(interviewers=10, reqs=6, history_reqs=12, applicants=30, interviewed=8)


def test_world_is_deterministic_and_groups_differ_only_in_access() -> None:
    a, b = make_company(3, SMALL), make_company(3, SMALL)
    assert [c.performance for r in a.reqs for c in r.candidates] == [
        c.performance for r in b.reqs for c in r.candidates
    ]
    big = make_company(4, dataclasses.replace(SMALL, reqs=60, applicants=60))
    cands = [c for r in big.reqs for c in r.candidates]
    perf = {gr: np.mean([c.performance for c in cands if c.group == gr]) for gr in "AB"}
    prestige = {gr: np.mean([c.prestige for c in cands if c.group == gr]) for gr in "AB"}
    assert abs(perf["A"] - perf["B"]) < 0.1
    assert prestige["A"] > prestige["B"] + 0.2
    assert sum(r.history for r in big.reqs) == SMALL.history_reqs
    assert SHIFTED.biased_share > Shape().biased_share and SHIFTED.history_reqs < Shape().history_reqs


def test_interviewer_biases_move_scores_as_described() -> None:
    co = make_company(5, SMALL)
    cand = co.reqs[0].candidates[0]
    fair = Interviewer(0, cand.group, 0.0, 0.0001, 0.0, 0.0, 0.0)
    lenient = dataclasses.replace(fair, leniency=1.0)
    partial = dataclasses.replace(fair, affinity=1.0)
    g = lambda: np.random.default_rng(1)  # noqa: E731
    base = rate(fair, cand, g())
    assert np.allclose(rate(lenient, cand, g()) - base, 0.8, atol=1e-3)
    assert np.allclose(rate(partial, cand, g()) - base, 0.8, atol=1e-3)
    other = dataclasses.replace(partial, group="B" if cand.group == "A" else "A")
    assert np.allclose(rate(other, cand, g()), base, atol=1e-3)
    school = dataclasses.replace(fair, prestige=1.0)
    star = dataclasses.replace(cand, prestige=True)
    assert np.allclose(rate(school, star, g()) - rate(fair, star, g()), 0.8, atol=1e-3)
    assert np.allclose(rate(school, star, g(), see_school=False), rate(fair, star, g()), atol=1e-3)
    assert resume_signal(star, g(), blind=False) - resume_signal(star, g(), blind=True) == 0.5


def test_leniency_is_recovered_from_panels() -> None:
    co = make_company(6, Shape())
    lean = leniency(history_ratings(co, 99))
    est = [lean[i.id] for i in co.interviewers]
    true = [i.leniency for i in co.interviewers]
    assert np.corrcoef(est, true)[0, 1] > 0.9
    assert abs(sum(est)) < 1e-6  # centred


def test_audit_flags_an_interviewer_who_favours_their_group() -> None:
    ratings = []
    g = np.random.default_rng(0)
    groups = {0: "A", 1: "A", 2: "B"}
    for c in range(80):
        grp = "A" if c % 2 else "B"
        level = float(g.normal())
        for i in groups:
            bonus = 0.8 if i == 0 and grp == "A" else 0.0
            ratings.append(Rating(0, c, grp, i, level + bonus + float(g.normal(0, 0.2))))
    flags = {f.interviewer: f for f in audit(ratings, groups, 0.3, 2.0)}
    assert flags[0].flagged and flags[0].gap > 0.5
    assert not flags[1].flagged and not flags[2].flagged
    few = audit(ratings[:12], groups, 0.3, 2.0)
    assert not any(f.flagged for f in few)  # too few scores to say


def test_every_process_sees_the_same_applicants_and_hires_the_same_number() -> None:
    co = make_company(8, SMALL)
    hist = history_ratings(co, 1)
    lean = leniency(hist)
    out = {p: run(co, p, 3, lean, set()) for p in PROCESSES}
    for p, os_ in out.items():
        assert len(os_) == SMALL.reqs
        assert all(len(o.hired) == SMALL.hires and len(o.interviewed) == SMALL.interviewed for o in os_)
        assert [o.applicants[0].id for o in os_] == [o.applicants[0].id for o in out["gut"]]
        panel = 1 if p == "gut" else 3
        assert all(len(o.ratings) == SMALL.interviewed * panel for o in os_)
    s = summary(out["structured"])
    assert s["hires"] == SMALL.reqs * SMALL.hires and 0 <= s["hires_top_decile"] <= 1 and s["impact_ratio"] >= 0


def test_flagged_interviewers_sit_out_only_in_the_fair_process() -> None:
    co = make_company(9, SMALL)
    lean = leniency(history_ratings(co, 1))
    out = run(co, "audited", 2, lean, {0, 1})
    assert all(r.interviewer not in (0, 1) for o in out for r in o.ratings)
    plain = run(co, "structured", 2, lean, {0, 1})
    assert any(r.interviewer in (0, 1) for o in plain for r in o.ratings)
