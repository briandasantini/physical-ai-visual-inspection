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
with one model and no contours. Review accuracy, precision, recall, F1, and every incorrect
row. Repeat for the categories that matter most, especially Shift/Displace.

## 3. Add contours

Rerun the exact same first examples and larger-set sample. This time send the OpenCV
contour view with the reference and live images. Compare:

- Did PASS/FAIL change?
- Did the explanation become more specific and grounded?
- Did contours introduce a false alarm?
- Which failure category still needs a human or conventional vision control?

Saved results and fresh NIM versions can differ. Compare only runs that use the same
labeled image pairs and input settings.

## Optional exploration

After the three required passes, test a controlled workspace capture or another dataset pair.
Change one physical variable at a time and write the expected result before inference.

## Interpretation rule

A correct verdict with an invented explanation is not a clean success. A model PASS never
authorizes a robotic run during this workshop.
