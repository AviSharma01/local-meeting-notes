# Failures

Bad outputs seen in real use. Each entry becomes an eval case before it is fixed.

Do not paste real transcript text, names, or companies here. This file is tracked. Put the real case in `evals/private/<case-name>/` and describe the failure in general terms.

## Template

### YYYY-MM-DD: short description

- Mode: debrief | meeting
- Model: e.g. qwen2.5:7b
- Field: e.g. commitments
- Expected: what should have been extracted, in general terms
- Got: what was extracted instead, in general terms
- Eval case: `evals/cases/<name>` or `evals/private/<name>`
- Status: open | fixed in <commit>

## 2026-09-29: other-party commitment keeps first-person wording

- Mode: debrief
- Model: qwen2.5:14b
- Field: commitments
- Expected: a commitment owned by the other party is worded from the speaker's point of view ("Get back to the speaker within a week about the next round.")
- Got: the task keeps the other party's first-person wording ("Get back to me within a week about the next round."); owner and due date are correct
- Eval case: `evals/cases/debrief-northwind-technical`
- Status: open
