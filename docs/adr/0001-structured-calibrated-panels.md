# 1. Hire on independent rubric scores with each interviewer's leniency taken out

## Context

Most hiring decisions rest on interviews, and interviews are noisy in ways that are well known: one interviewer's
overall impression, an open debrief where the first or most senior voice anchors the rest, interviewers who are
simply harsher or kinder than their colleagues, and a halo where one strong impression colours every competency.
Different candidates meet different panels, so a candidate who happened to meet two lenient interviewers is ahead
before anything else is considered.

## Decision

- **A panel of three scores a rubric per competency, independently, before any discussion.** Scores are weighted by
  the role's competency weights and averaged. The debrief comes after the scores are in.
- **Leniency is learned and taken out.** Each past score is modelled as candidate level + interviewer leniency +
  noise and fitted by alternating least squares over the previous quarter's panels. Estimates are shrunk towards
  zero (5 pseudo-ratings, chosen on the tuning companies from 0, 2, 5, 10 and 20), so a new interviewer is barely
  adjusted. The adjustment is the same for every candidate an interviewer sees.

## Results

Simulated companies; quality is the true job performance of the people hired, in standard deviations of the
applicant pool. Held-out companies (15 companies, 27,000 applicants, 900 hires):

| Process | Hire performance | Hires in the top 10% |
|---|---:|---:|
| One interviewer's overall impression | +0.65 | 40% |
| Panel of three, open debrief | +0.75 | 49% |
| Panel of three, independent rubric scores | +0.80 | 52% |
| **Rubric scores, leniency taken out** | **+0.88** | **59%** |

In the shifted companies (more spread in leniency, less history) calibration helped more: +0.89 against +0.75 for
uncalibrated panels.

## Consequences

- **Precision makes bias more decisive.** On held-out companies the hire-rate ratio between groups *fell* from 0.58
  to 0.53 when leniency was taken out. Removing noise leaves a consistent bias (an interviewer favouring their own
  group, credit for a well-known school) as a bigger share of what separates candidates. Better measurement does not
  fix fairness by itself; ADR 2 does that part.
- Leniency estimates track the truth closely (r = 0.96 held-out), but only for interviewers with history.
- The rubric and the weights must be written per role before interviewing; the console shows the competencies and
  every panel member's raw score and adjustment.
