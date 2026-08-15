# Workshop Map

The required workshop contains three passes over labeled visual evidence, followed by an
optional controlled exploration.

| Phase | Question | Required evidence | Suggested time |
|---|---|---|---:|
| [First examples](first-examples.md) | Can the models describe obvious and subtle changes? | Baseline results for five curated pairs | 25 min |
| [Larger set](larger-set.md) | Do the observations hold across a labeled sample? | Metrics plus review of every incorrect row | 35 min |
| [Add contours](contours.md) | Do pixel-level cues change verdicts or grounding? | Matched baseline/contour comparison | 30 min |
| [Explore](explore.md) | What controlled test should we try next? | One hypothesis and one-variable experiment | Optional |

## Evidence checklist

- [ ] Reason2 8B is ready.
- [ ] First-example expectations are recorded.
- [ ] First-example baseline is complete.
- [ ] Baseline explanations are reviewed.
- [ ] Larger-set baseline is complete.
- [ ] The same evidence is rerun with contours.
- [ ] The weakest category is identified.
- [ ] Evidence is exported and the finding is recorded.

## How to score a response

Evaluate each result on two independent axes:

1. **Verdict:** Does the returned `PASS` or `FAIL` match the label?
2. **Explanation:** Does the response name the real object, change, and location without
   inventing unsupported differences?

A correct verdict with an invented explanation is not a clean success.
