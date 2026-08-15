# 1. First Examples

Start with five curated pairs. Do not add contours until every baseline result has been
reviewed.

## Required order

1. Same image — expected `PASS`
2. Single object removed — expected `FAIL`
3. Larger configuration change — expected `FAIL`
4. Unexpected object — expected `FAIL`
5. Subtle displacement — expected `FAIL`

## Browser exercise

1. Open **1 · First Examples**.
2. Load the first pair and read its label.
3. Write what you expect each model to observe.
4. Select **A · Run baseline**.
5. Review the verdict table and raw reasoning.
6. Mark correct details, misses, and hallucinations.
7. Repeat for all five pairs.
8. Download the baseline JSON evidence.

## What to record

| Field | Example question |
|---|---|
| Expected label | Was a physical difference intentionally introduced? |
| Verdict correctness | Did the model return the labeled result? |
| Grounded observation | Did it name a visible, relevant difference? |
| Unsupported claim | Did it invent an object, location, or change? |
| Model comparison | Did 2B and 8B fail in the same way? |

!!! tip
    Preserve the raw response. Short summaries can hide uncertainty or hallucinated
    details that matter to the evaluation.

Do not run the contour-assisted button yet. First establish what the models can infer
from the original image pair alone.
