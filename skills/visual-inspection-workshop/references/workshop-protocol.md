# Workshop protocol

## Question

Can a vision-language model compare an expected workspace with an observed workspace, return
the right PASS/FAIL result, and explain the real physical change without inventing one?

## Repeated loop

1. Read the labeled pair.
2. Record the expected PASS/FAIL result before inference.
3. Run the selected model and input mode.
4. Judge verdict and explanation separately.
5. Save JSON evidence.
6. Change one input and repeat on the same pair.

## Phase 1: first examples

Run the curated first examples without contours in this order:

- matching images (`PASS`);
- one removed object (`FAIL`);
- a larger configuration change (`FAIL`);
- an unexpected object (`FAIL`);
- a subtle displacement (`FAIL`).

Compare available models' verdicts, correct observations, misses, hallucinations, and
latency. Complete baseline review before introducing contours.

## Phase 2: larger set

Select a category and fixed ordered sample from the labeled evaluation collection. Run
baseline with one model. Review aggregate metrics and every incorrect row. Prioritize
Shift/Displace because subtle movement is the known weak category.

## Phase 3: contour assistance

Rerun the exact same first examples and larger-set sample with the OpenCV contour view.
Compare verdict changes, explanation grounding, newly recovered errors, and false alarms.

Contour configuration is threshold 25 and minimum area 3000. Red boxes are attention
hints, not proof of a physical change.

A correct verdict with an invented explanation is not a clean success. Preserve each
run as evidence and compare only experiments that use the same labeled pairs.

## Closing output

Summarize:

- strongest and weakest tested categories;
- verdict errors and explanation hallucinations;
- effect of contour assistance;
- capture, conventional-vision, VLM, and infrastructure failures separately;
- required human controls and the next validation gate.
