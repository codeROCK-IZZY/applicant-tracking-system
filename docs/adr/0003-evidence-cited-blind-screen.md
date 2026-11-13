# 3. The résumé screen reads a redacted résumé, cites its evidence, and never rejects on its own

## Context

Résumé screens are where schools, names and gaps in dates quietly decide who gets an interview. A language model
reads résumés far better than keyword rules, but it can also pick up the same signals, and it can state a level
without anything in the résumé to support it.

## Decision

- **Redact first, in code.** The name line, contact details, the education section and dates of birth are removed
  before anything (rules or Claude) reads the résumé. What was removed is listed by kind, never by content.
- **Claude reads the rest** (`claude-opus-5-5`, low effort, refusal fallbacks) and fills a strict tool: for each of
  the role's competencies, a level from 1 to 5 and the exact words that show it. The system prompt tells it to judge
  only what the person has done and that text inside the résumé is never an instruction.
- **Code keeps only quoted evidence.** A level without a quote from the redacted résumé, or outside 1 to 5, is
  dropped with a reason.
- **Without a key, or on a refusal,** keyword rules give a rough level per competency.
- **Levels are evidence for a person,** shown next to their quotes. Nothing is rejected automatically.

## Consequences

- Redaction is pattern-based and will miss things (a school named in a job title, a photo caption in odd
  formatting). The tests cover the common layout.
- **The screen's accuracy is not measured here;** that would need paid calls over many résumés and labelled
  outcomes. The tests check the request shape, that nothing redacted is sent, and the evidence rules through the real
  SDK with canned responses.
- In the hiring simulation, the effect of hiding the school at the screen is measured directly (ADR 2).
