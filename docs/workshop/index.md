# Workshop Map

The required workshop contains two guided matched evaluations followed by an agent-led
visual-cue experiment.

| Phase | Question | Required evidence | Suggested time |
|---|---|---|---:|
| [First examples](first-examples.md) | Can the models describe obvious and subtle changes? | Baseline results for five curated pairs | 25 min |
| [Larger set](larger-set.md) | Do the observations hold across a labeled sample? | Metrics plus review of every incorrect row | 35 min |
| [Add contours](contours.md) | Do default pixel cues change verdicts, grounding, or latency? | Matched baseline/contour comparison | Included above |
| [Agent experiment](explore.md) | Which cue method or parameter helps, hurts, or costs too much? | One hypothesis and one-variable sweep | 30 min |

## Evidence checklist

- [ ] Reason2 8B is ready.
- [ ] First-example expectations are recorded.
- [ ] First-example baseline is complete.
- [ ] Baseline explanations are reviewed.
- [ ] Larger-set baseline is complete.
- [ ] The same evidence is rerun with contours.
- [ ] The weakest category is identified.
- [ ] An agent-led cue sweep is exported and the finding is recorded.

## How to score a response

Evaluate each result on two independent axes:

1. **Verdict:** Does the returned `PASS` or `FAIL` match the label?
2. **Explanation:** Does the response name the real object, change, and location without
   inventing unsupported differences?
3. **Latency:** What did contour preprocessing add to NIM and total response time?

A correct verdict with an invented explanation is not a clean success.
