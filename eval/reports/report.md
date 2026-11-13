# Applicant tracking: evaluation

Simulated companies hiring: candidates with a true ability nobody sees, interviewers who differ in leniency, consistency, halo and (for some) bias towards their own group. Quality is the true job performance of the people hired, in standard deviations; fairness is group B's hire rate over group A's (below 0.8 fails the four-fifths rule).

Chosen on the tuning companies: leniency shrinkage 5.0 pseudo-ratings; audit flags a gap over 0.4 with t over 2.0.

## Held-out companies: 15 companies, 27,000 applicants

| Process | Hire performance | Hires in top 10% | Impact ratio (B/A) | Companies below 4/5 |
|---|---:|---:|---:|---:|
| One interviewer's overall impression | +0.65 | 40% | 0.67 | 12 of 15 |
| Panel of three, open debrief | +0.75 | 49% | 0.60 | 12 of 15 |
| Panel of three, independent rubric scores | +0.80 | 52% | 0.58 | 11 of 15 |
| Rubric scores, interviewer leniency taken out | +0.88 | 59% | 0.53 | 15 of 15 |
| Calibrated + school hidden + flagged interviewers off panels | +0.91 | 63% | 0.97 | 9 of 15 |

Audit: 37 of 53 biased interviewers found, 1 false flags (1% of the others). Leniency estimates vs truth: r = 0.96.

## Shifted companies (held back): more bias, less history: 8 companies, 14,400 applicants

| Process | Hire performance | Hires in top 10% | Impact ratio (B/A) | Companies below 4/5 |
|---|---:|---:|---:|---:|
| One interviewer's overall impression | +0.60 | 36% | 0.49 | 6 of 8 |
| Panel of three, open debrief | +0.71 | 45% | 0.46 | 8 of 8 |
| Panel of three, independent rubric scores | +0.75 | 47% | 0.43 | 6 of 8 |
| Rubric scores, interviewer leniency taken out | +0.89 | 59% | 0.39 | 7 of 8 |
| Calibrated + school hidden + flagged interviewers off panels | +0.92 | 61% | 0.80 | 6 of 8 |

Audit: 27 of 66 biased interviewers found, 0 false flags (0% of the others). Leniency estimates vs truth: r = 0.95.

## Tuning companies: 6 companies, 10,800 applicants

| Process | Hire performance | Hires in top 10% | Impact ratio (B/A) | Companies below 4/5 |
|---|---:|---:|---:|---:|
| One interviewer's overall impression | +0.69 | 44% | 0.65 | 4 of 6 |
| Panel of three, open debrief | +0.77 | 50% | 0.54 | 5 of 6 |
| Panel of three, independent rubric scores | +0.84 | 55% | 0.48 | 6 of 6 |
| Rubric scores, interviewer leniency taken out | +0.93 | 64% | 0.59 | 6 of 6 |
| Calibrated + school hidden + flagged interviewers off panels | +0.96 | 66% | 0.85 | 5 of 6 |

Audit: 10 of 13 biased interviewers found, 0 false flags (0% of the others). Leniency estimates vs truth: r = 0.98.

## Tuning

| Leniency shrinkage | Calibrated hire performance |
|---:|---:|
| 0.0 | +0.928 |
| 2.0 | +0.933 |
| 5.0 | +0.935 |
| 10.0 | +0.929 |
| 20.0 | +0.926 |

| Audit gap | t | Biased found | False flags |
|---:|---:|---:|---:|
| 0.2 | 2.0 | 92% | 7% |
| 0.2 | 2.5 | 69% | 0% |
| 0.2 | 3.0 | 69% | 0% |
| 0.3 | 2.0 | 92% | 4% |
| 0.3 | 2.5 | 69% | 0% |
| 0.3 | 3.0 | 69% | 0% |
| 0.4 | 2.0 | 77% | 0% |
| 0.4 | 2.5 | 69% | 0% |
| 0.4 | 3.0 | 69% | 0% |

## Gate (limits written before the held-out run)

- PASS heldout_calibrated_over_gut_min: 0.226 (limit 0.15)
- PASS heldout_fair_impact_ratio_min: 0.971 (limit 0.8)
- PASS heldout_fair_not_worse_than_structured: 0.1185 (limit 0.0)
- PASS heldout_audit_recall_min: 0.6981 (limit 0.5)
- PASS heldout_audit_false_flag_rate_max: 0.0064 (limit 0.05)
- PASS shifted_calibrated_over_gut_min: 0.2846 (limit 0.1)
- PASS shifted_fair_impact_ratio_min: 0.7963 (limit 0.75)
