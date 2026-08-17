# Workshop Map

The workshop moves from concrete model behavior to application questions and a data plan.
Each phase should create a conversation, not just an exported score.

| Phase | Explore together | Useful evidence |
|---|---|---|
| [1 · First examples](first-examples.md) | Where do 2B and 8B succeed, miss, disagree, or hallucinate? | Images plus original responses and semantic observations |
| [2 · Larger set](larger-set.md) | Which patterns generalize, and which new failure types appear? | Verdict/action/object metrics plus selected rows |
| [Contour cues](contours.md) | Do cues help detection, hurt semantics, or create false alarms? | Matched baseline/contour cases |
| [3 · Agent experiment](explore.md) | What should we investigate next about prompts, cues, tolerances, gaps, or data? | One focused exploration and its implication |

## Keep these questions open

- Is the model right for the right physical reason?
- Does a contour change only the verdict, or also action and object quality?
- Which error is worse here: a false alarm or a missed change?
- What physical deviation should be accepted, rejected, or sent to human review?
- Which object, action, nuisance condition, or edge case have we not tested?
- What would an ideal case and a difficult but realistic counterexample look like?
- What data and held-out test would justify fine-tuning?

## Read evidence on separate axes

1. **Verdict:** Does the result match the dataset reference label?
2. **Semantics:** Does it name the real action, object, and location?
3. **Hallucination:** Does it invent unsupported physical evidence?
4. **Cue effect:** Did contours help, hurt, or merely change confidence?
5. **Error trade-off:** What do false alarms and missed changes mean operationally?
6. **Coverage:** Is the case set missing something important?
7. **Latency:** Is the observed benefit worth the preprocessing and total cost?

A correct verdict with an invented explanation is not a clean success, and a good
aggregate score can still hide the error type that matters most.
