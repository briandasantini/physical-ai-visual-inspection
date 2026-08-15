---
name: visual-inspection-workshop
description: Guide and evaluate a Physical AI visual inspection workshop using the launchable CLI, labeled image-pair collections, NVIDIA Cosmos Reason2 or optional Cosmos3 Nano, and baseline-versus-contour reasoning comparisons. Use when an agent needs to check workshop readiness, explain or run exercises, inspect image pairs, compare model reasoning, evaluate a labeled batch, interpret metrics, export evidence, troubleshoot the Brev environment, or help participants choose the next exercise.
---

# Visual Inspection Workshop

Operate the workshop through its supported CLI and preserve the experiment's order and
labels. Guide the participant; do not turn a model verdict into robotic authorization.

## Locate and preflight

1. Run `scripts/run-visual-inspection.sh status` from this skill directory.
2. Require Reason2 8B to be `READY` before an exercise.
3. Treat Reason2 2B as a comparison model and Nano as optional.
4. Confirm the configured curated and evaluation collections are available.
5. If readiness fails, read `references/environment.md` before changing services.

The helper locates the repository and calls its `./vision-inspect` command. Prefer it over
direct NIM API calls so the website and agent use identical prompts and parsing.

## Choose the workflow

- **Teach or continue the workshop:** follow the three phases in
  `references/workshop-protocol.md` in order.
- **Inspect one labeled pair:** list pairs, record the expected label, then run both
  baseline and contour modes.
- **Compare models:** use the same pair and input mode for each selected model.
- **Evaluate a category:** run a small fixed sample baseline first, then rerun the same
  sample with contours.
- **Test a custom workspace pair:** require expected, observed, and a participant-written
  expected result before inference.
- **Use Nano:** read `references/environment.md`; activate it only when explicitly
  requested because it replaces Reason2 2B on GPU 0.

## Run supported commands

```bash
# Discover the labeled exercise data.
scripts/run-visual-inspection.sh pairs --collection round1

# Compare reasoning on one pair.
scripts/run-visual-inspection.sh inspect --pair <pair-id> \
  --models reason2-2b reason2-8b --mode both --raw \
  --output evidence/r1-pliers.json

# Run the curated-example phase.
scripts/run-visual-inspection.sh round1 --models reason2-8b --mode baseline \
  --output evidence/round1-baseline.json

# Compare a larger-set sample in both modes.
scripts/run-visual-inspection.sh batch --category Shift/Displace --count 10 \
  --model reason2-8b --mode both \
  --output evidence/shift-10.json
```

Keep interactive batches at 10 pairs unless the user requests a different count. Warn
before running a large or full-corpus evaluation because every pair invokes a NIM.

## Evaluate evidence

For every result, report these separately:

1. Whether the verdict matches the labeled expected result.
2. Whether the explanation names the real object and location.
3. Whether the explanation invents unsupported changes.
4. Whether contour assistance changes the verdict or grounding.
5. Latency as a secondary consideration after correctness.

Treat `FAIL` as the positive class for precision, recall, and F1. Do not reinterpret or
rewrite dataset labels to match a model. Distinguish saved historical results from a new
rerun, which may differ.

## Guardrails

- Never present `PASS` as permission to release an automated run.
- Never expose, print, copy into Git, or include the NGC key in evidence.
- Never add private images, archives, or generated evidence to Git.
- Never run Nano and Reason2 2B together; they share GPU 0.
- Never hide incorrect verdicts, hallucinations, or Shift/Displace misses.
- Never modify the original reference/live images or expected labels.
- Ask before stopping Brev, switching model sets, or running a large batch.
