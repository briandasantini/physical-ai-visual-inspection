# Visual inspection workshop flow

## Why we are here

The workshop is a joint investigation of the useful operating envelope for visual
inspection—not a PASS/FAIL certification exercise. The labeled pairs let us ask where a
vision-language model is helpful, where it misses or hallucinates, and what the real
application should require.

Together, explore:

- which objects and physical changes the models understand reliably;
- where the verdict is right but the action, object, or location is wrong;
- whether contour cues improve detection, distort semantics, or create false alarms;
- which false positives or false negatives are more costly for the intended workflow;
- what physical tolerance should separate an acceptable setup from a meaningful error;
- which object types, actions, nuisance conditions, and edge cases are missing;
- what additional evidence is needed before prompt changes, conventional vision, or
  fine-tuning would be justified.

## Working loop

1. Choose a question about the model or intended application.
2. Inspect a few labeled cases and preserve the original model responses.
3. Separate verdict quality from action, object, location, and unsupported claims.
4. Compare the same cases across models or with and without contour cues.
5. Look for a recurring pattern—and actively search for a case that contradicts it.
6. Translate the finding into a product requirement, missing-case list, or next experiment.

Dataset labels are reference annotations for scoring. Participants do not need to predict
or retype them. If a label or image is ambiguous, record that as a data finding rather
than silently changing the label to match the model.

## 1. First examples

Use five curated cases that introduce a matching setup, removal, configuration change,
unexpected object, and subtle displacement. Run reference + live first so the model's
unaided behavior is visible. Compare the models' correct observations, misses,
hallucinations, action/object grounding, and uncertainty. Then add contours to the same
cases and ask what changed.

## 2. Larger set

Choose a category and fixed sample of the larger labeled set. Inspect accuracy, precision,
recall, F1, action accuracy, item accuracy, latency, and individual raw responses. Use
precision to discuss false-alarm cost and recall to discuss missed-change cost; neither is
the default objective until the intended workflow defines the trade-off. Repeat the same
ordered sample with contours and look for both improvements and new failure modes.

## 3. Agent experiment

Use the Jupyter terminal and ask Codex or Claude to investigate one open question. That
question can concern model reasoning, prompts, contours, acceptable tolerances, error
trade-offs, missing cases, or fine-tuning data.

For a contour experiment, keep the model and inspection prompt fixed while varying one
factor:

- difference method: color, channel maximum, or edges;
- pixel threshold;
- minimum contour area.

For any experiment, compare matched cases and preserve the raw response. Explain whether
the result changed detection, action/object quality, hallucinations, or only latency.

## Define the ideal case

Describe an ideal inspection case for the intended workflow. Specify the object,
meaningful change, acceptable tolerance, nuisance variation, and consequence of a false
alarm versus a missed change. If the case is not represented, record it as a data gap.
Unlabeled custom images are qualitative exploration until a domain expert supplies a
trustworthy annotation policy.

## Interpretation rule

A correct verdict with an invented explanation is not a clean success. A high aggregate
score can also hide an unacceptable error type. Misses, hallucinations, ambiguous labels,
and missing cases are useful findings when the evidence and configuration are preserved.
