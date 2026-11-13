# 2. Hide the school, audit interviewers against their co-panelists, and never adjust a candidate's score by group

## Context

In the simulated companies both groups of candidates have the same ability. Group A more often went to a
well-known school, which says nothing about ability, and most interviewers are from group A. A quarter of
interviewers score their own group higher. With plain structured panels, group B's hire rate was 0.58 of group A's on
held-out companies, below the four-fifths line (0.8) that is the usual evidence of adverse impact.

The tempting fix is to adjust scores by group. That is a bad idea and, for selection tests in the US, unlawful
(adjusting scores on the basis of a protected characteristic). Group membership must not change any individual's
score.

## Decision

- **Hide the school** from the résumé screen and from the interview packet. The screen reads what the person has
  done; the interviewers score the rubric.
- **Audit interviewers against their co-panelists.** For each interviewer, compare every past score with the mean of
  the other panel members' scores for the same candidate, separately for candidates of the interviewer's own group
  and of other groups. A gap above a threshold, with enough scores of each kind and a clear t statistic, flags the
  interviewer **for a person to review**. Until reviewed, they don't sit on panels. Thresholds were chosen on the
  tuning companies: the highest recall with false flags at or below 3% of unbiased interviewers.
- **Group data is collected voluntarily, kept apart from applications, and only used in aggregate**: for the audit
  and the four-fifths check by stage.

## A fix after the first held-out run

A unit test written after the first held-out run found that one biased interviewer inflates the co-panel mean for
the group they favour, so an **unbiased colleague of the other group looks biased**. The audit now flags one
interviewer at a time, clearest first, and takes each flagged interviewer's scores out of the co-panelist comparison
before looking again. The audit thresholds were tuned again on the tuning companies (gap 0.4 instead of 0.3, t 2.0),
and every bank was run again.

| | First run | After the fix |
|---|---:|---:|
| Held-out: biased interviewers found | 40 of 53 | 37 of 53 |
| Held-out: false flags | 3 (1.9%) | 1 (0.6%) |
| Held-out: hire-rate ratio B/A, fair process | 0.98 | 0.97 |
| Shifted: biased interviewers found | 30 of 66 | 27 of 66 |
| Shifted: false flags | 1 | 0 |
| Shifted: hire-rate ratio B/A, fair process | 0.75 | 0.80 |

## Results

| Hire-rate ratio B/A | Held-out | Shifted |
|---|---:|---:|
| Panel of three, independent rubric scores | 0.58 | 0.43 |
| Rubric scores, leniency taken out | 0.53 | 0.39 |
| **Calibrated + school hidden + flagged interviewers off panels** | **0.97** | **0.80** |

The fair process also hired the best people (+0.91 held-out), because hiding the school and removing biased scores
takes out error, not information.

## Consequences

- **The pooled ratio hides companies where bias remains.** Checked per company and in both directions (the lower
  group's rate over the higher's), 9 of 15 held-out companies were still below four-fifths under the fair process.
  With no biased interviewers at all, chance alone puts 1 of 15 below. The difference is the biased interviewers the
  audit did not find (16 of 53).
- **The audit needs history.** In the shifted companies (fewer past panels per interviewer) it found 27 of 66 biased
  interviewers, and 6 of 8 companies were still below four-fifths on their own, though the pooled ratio reached 0.80.
- The four-fifths check was first written one-sided (group B's rate over group A's). The console showed a company
  where group A was hired at 0.6 of group B's rate marked as passing. The check now works in both directions, in the
  console, the per-company counts and the gate; the pooled results above did not change.
- A flag is a reason for a conversation, not a verdict: the console shows the gap, the t statistic and how many
  scores it rests on.
- Small companies have too few hires for the four-fifths ratio to mean much per requisition; the console shows it
  per stage for the quarter.
