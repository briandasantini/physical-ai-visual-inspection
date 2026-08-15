# 3. Add Contours

Contour assistance adds a third image containing pixel-level change cues. It is an
experimental input—not a finished detection solution.

## Matched comparison

Rerun the **exact same pairs, model, and sample selection** used during baseline.

1. Return to **1 · First Examples** and select **B · Run with contours**.
2. Compare baseline and contour reasoning for each curated pair.
3. Return to **2 · Larger Set** and select **B · Rerun same set with contours**.
4. Select **C · Compare larger-set metrics**.
5. Export the contour evidence.

## Questions to answer

- Did the `PASS` or `FAIL` verdict change?
- Did the explanation identify the real object and location more precisely?
- Did contours introduce a false alarm?
- Did the model merely mention the overlay rather than reason about the workspace?
- Which category remains difficult after visual guidance?

## Interpret carefully

Contour cues may focus attention, but they do not explain what changed. Improvement on
one pair does not establish a general solution. A useful conclusion distinguishes:

- verdict improvement;
- explanation improvement;
- regressions caused by added visual cues;
- unchanged failures that may require better data or post-training.

Finish with a matched statement:

> For the same ___ pairs, contour assistance changed ___ verdicts, improved grounding
> on ___, introduced ___ regressions, and did not solve ___.
