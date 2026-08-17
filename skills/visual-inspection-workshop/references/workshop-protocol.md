# Workshop protocol

## Purpose

Collaboratively characterize where the visual-inspection stack is useful, unreliable, or
underspecified. The goal is not to make participants guess PASS/FAIL labels. Existing
labels are reference annotations that make model behavior measurable.

## Questions to keep open

- Where does each model detect and explain the real physical change?
- Where does it miss a change or hallucinate an unsupported object, action, or location?
- Do contours improve detection while degrading action or object grounding?
- Which false positives or false negatives are more costly for the intended workflow?
- What physical displacement, angle, occupancy, or object difference should be tolerated?
- Which object types, actions, nuisance conditions, or edge cases are absent?
- What data and held-out evaluation would be necessary before fine-tuning?

## Working loop

1. Choose one question about the model or intended application.
2. Inspect a small set of labeled cases and preserve original responses.
3. Judge verdict, action, object, location, hallucinations, and uncertainty separately.
4. Compare the same cases across models or with and without contours.
5. Search for both a recurring pattern and a counterexample.
6. Translate the finding into a product requirement, missing-case list, or next experiment.

Do not alter labels to match a model. Record ambiguous labels or unclear images as data
findings. Treat unlabeled custom images as qualitative exploration until a domain expert
defines a trustworthy annotation policy.

## Phase 1: first examples

Use the curated examples to discover the models' unaided behavior. Compare 2B and 8B on
correct observations, misses, hallucinations, semantic grounding, and uncertainty. Add
contours to the same cases and ask whether verdict, action, object, or location changes.

## Phase 2: larger set

Select a category and fixed ordered sample. Inspect verdict, action, item, and latency
metrics together with individual raw responses. Interpret precision as false-alarm
behavior and recall as missed-change behavior; ask which cost the intended workflow can
tolerate. Look for new failure types that the curated examples did not reveal.

## Phase 3: agent experiment

Use Codex or Claude to investigate one open question. A controlled contour sweep is one
option: keep the model and prompt fixed while varying difference method, threshold, or
minimum area. Prompt comparison, missing-case inventory, tolerance definition, error-cost
analysis, and fine-tuning data planning are equally valid directions.

For any experiment, compare matched evidence and explain whether the change affects
detection, action/object grounding, hallucinations, or only latency. Ask before a large
batch or model-service switch.

## Closing conversation

Summarize:

- strongest and weakest observed behaviors, with counterexamples;
- hallucinations and semantic errors hidden by correct verdicts;
- contour benefits and regressions;
- the desired false-positive/false-negative trade-off and physical tolerance;
- missing objects, actions, nuisance conditions, and ideal cases;
- whether the next investment should be requirements work, data collection, conventional
  vision, prompt design, or fine-tuning;
- the evidence and held-out test needed for the next decision.
