# Known limitations

- **It is a simulation.** Abilities, interviewer biases and job performance are generated, so the results show how
  the methods behave when interviewers differ in these ways, not how much they would change a real company's hires.
  The biases modelled (leniency, noise, halo, own-group affinity, credit for a school) are well documented; their
  sizes here are assumptions.
- **Two groups only,** and group membership is known for everyone in the simulation. Real voluntary self-reporting
  is incomplete, and there are many groups and intersections.
- **The audit needs history.** It found 70% of biased interviewers on held-out companies, and 41% in the shifted
  companies where there were fewer past panels. Interviewers with little history are neither calibrated nor audited.
- **One design fix was made after the first held-out run** (the audit peeling, ADR 2); both runs are reported.
- **Per company, bias remains.** Checked in both directions, the fair process was below four-fifths in 9 of 15
  held-out companies, although the pooled ratio was 0.97; chance alone would explain about 1 of 15.
- **The résumé screen is not measured** for accuracy, and redaction is pattern-based (ADR 3).
- **The console is a demo:** one company held in memory, no logins, no scheduling, no candidate communications.
