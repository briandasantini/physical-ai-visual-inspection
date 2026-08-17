# Understand Contour Cues

Contour assistance adds a third image containing pixel-level change regions. It is an
attention cue—not proof of a defect and not a finished detection solution.

## Compare matched cases

Use the exact same pairs and model for baseline and contour-assisted runs. In **First
Examples**, compare the two responses directly. In **Larger Set**, compare aggregate
metrics and then select individual rows to inspect the images and original reasoning.

## Ask more than “did accuracy improve?”

- Did the verdict change from a miss to a grounded detection?
- Did action or object quality improve, regress, or stay wrong?
- Did the model invent an object or describe the red overlay as physical evidence?
- Did a nuisance change such as lighting create a false alarm?
- Did the cue help one category while hurting another?
- Did the cue change confidence without improving the explanation?
- Is the preprocessing and total latency worth the observed benefit?
- Does the result suggest a missing case or an undefined physical tolerance?

## Interpret the trade-off

Contours can increase recall by attracting attention to subtle differences, but they can
also lower precision through false alarms or steer the model toward the wrong action or
object. The useful setting depends on the intended workflow: the cost of a missed change,
the cost of unnecessary review, and the amount of physical variation that should be
accepted.

One pair is a clue, not a conclusion. Look for the same effect on a matched sample and
actively search for a counterexample.
