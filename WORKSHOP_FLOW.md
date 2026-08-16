# Visual inspection workshop flow

## Question

Can a vision-language model compare an expected workspace with an observed workspace, return
the right PASS/FAIL result, and explain the real physical change without inventing one?

## Repeated loop

1. Read the labeled pair and write the expected PASS/FAIL result.
2. Run the model.
3. Judge the verdict and explanation separately.
4. Save the evidence.
5. Change one input and repeat on the same pair.

## 1. First examples

Use five curated pairs in this order:

1. Baseline — Same Image (`PASS`)
2. Single object removed (`FAIL`)
3. Larger configuration change (`FAIL`)
4. Unexpected object (`FAIL`)
5. Subtle displacement (`FAIL`)

Run reference + live only. Compare the available models' verdicts, correct observations,
misses, and hallucinations. Do not add contours until all five baseline runs are reviewed.

## 2. Larger set

Choose a category and a fixed sample of the larger labeled evaluation set. Run the sample
with one model and no contours. Review accuracy, precision, recall, F1, action accuracy,
item accuracy, NIM latency, and raw examples. Repeat the same ordered sample with default
contours and inspect every incorrect row.

## 3. Agent cue experiment

Use the persistent side terminal and ask Codex or Claude to design a small controlled sweep.
Keep the model and inspection prompt fixed while varying one contour factor:

- difference method: color, channel maximum, or edges;
- pixel threshold;
- minimum contour area.

Compare verdict, action, item, contour regions, changed-pixel ratio, preprocessing latency,
NIM latency, and total latency. Saved results and fresh NIM versions can differ, so compare
only matched runs.

## Optional exploration

After the three required passes, test a controlled workspace capture or another dataset pair.
Change one physical variable at a time and write the expected result before inference.

## Interpretation rule

A correct verdict with an invented explanation is not a clean success. Misses are useful
evidence when the pair, prompt, model, and cue settings are preserved.
