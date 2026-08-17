# 2. Larger Set

The curated examples suggest hypotheses. The larger labeled set shows whether those
patterns recur—and whether entirely new failure modes appear.

## Explore a sample

1. Open **2 · Larger Set**.
2. Choose a category, model, and manageable sample size.
3. Run the baseline, then rerun the same ordered pairs with contours.
4. Compare the aggregate metrics, but do not stop there.
5. Select rows in either table to view the images side by side, original response,
   normalized scoring response, semantics, latency, and configured prompt bundle.

Keep an interactive batch to roughly ten pairs unless the group chooses a larger run.
Every pair invokes a NIM.

## Turn metrics into application questions

- **Accuracy:** How often is the overall verdict right?
- **Precision:** How often is a reported problem real? Low precision means more false
  alarms and potentially more unnecessary human review.
- **Recall:** How many real problems are found? Low recall means more missed changes.
- **F1:** How balanced are precision and recall? It does not decide which error is more
  expensive for the real workflow.
- **Action %:** When a defect is detected, does the response identify what happened?
- **Object %:** Does it identify the relevant object or labware?
- **Latency:** Is any quality gain worth the NIM, preprocessing, and total response time?

Ask explicitly: should this use case favor fewer false alarms, fewer missed changes, or a
human-review band? What physical displacement, angle, occupancy change, or object
difference should be tolerated before the system reacts?

## Inspect the rows behind the score

Look for:

- correct verdicts with wrong actions or objects;
- hallucinated changes in otherwise matching setups;
- missed small, subtle, or low-contrast changes;
- contour improvements that do not improve semantic grounding;
- contour regressions or illumination-driven false alarms;
- a new object, action, nuisance condition, or edge case absent from the curated set;
- ambiguous labels or images that need domain review.

Finish with a short operating hypothesis: where the model appears useful, the error type
that matters most, the tolerance still needing definition, and the next missing case to
collect or test.
