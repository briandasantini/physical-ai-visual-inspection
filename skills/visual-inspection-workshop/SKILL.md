---
name: visual-inspection-workshop
description: Guide a collaborative Physical AI visual inspection workshop using the launchable CLI, labeled image-pair collections, NVIDIA Cosmos Reason2 or optional Cosmos3 Nano, and baseline-versus-contour comparisons. Use when an agent needs to characterize model strengths, misses, hallucinations, semantic grounding, error trade-offs, missing cases, tolerance requirements, or data needs; run matched experiments; interpret metrics; export evidence; or troubleshoot the Brev environment.
---

# Visual Inspection Workshop

Operate the workshop through its supported CLI and help participants discover the useful
operating envelope for their application. Preserve labels and matched evidence, but do
not turn the session into a label-prediction exercise or model leaderboard.

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
- **Inspect one labeled pair:** use its label as a reference, inspect raw reasoning, and
  compare baseline and contour modes.
- **Compare models:** use the same pair and input mode for each selected model.
- **Evaluate a category:** run a small fixed sample baseline first, then rerun the same
  sample with contours.
- **Run the agent lab:** investigate one open question about model reasoning, prompts,
  contours, error trade-offs, tolerances, missing cases, or data needs.
- **Test a custom workspace pair:** first define the intended behavior, meaningful physical
  tolerance, and cost of a false alarm versus a missed change. Treat it as qualitative
  exploration until a domain expert supplies a trustworthy label policy.
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

# Compare visual-cue methods and parameters on one labeled pair.
scripts/run-visual-inspection.sh sweep --pair <pair-id> --model reason2-8b \
  --diff-methods color channel-max edges \
  --thresholds 15 25 35 --min-areas 3000 \
  --output evidence/cue-sweep.json
```

Keep interactive batches at 10 pairs unless the user requests a different count. Warn
before running a large or full-corpus evaluation because every pair invokes a NIM.

## Evaluate evidence

For every result, report these separately:

1. Whether the verdict matches the labeled expected result.
2. Whether the explanation names the real object and location.
3. Whether the explanation invents unsupported changes.
4. Whether contour assistance changes the verdict or grounding.
5. NIM, preprocessing, and total latency after correctness and grounding.
6. Whether the pattern suggests a false-alarm risk, missed-change risk, ambiguous label,
   or missing object/action/nuisance case.

Treat `FAIL` as the positive class for precision, recall, and F1. Do not reinterpret or
rewrite dataset labels to match a model. Explain that precision reflects false-alarm
behavior and recall reflects missed-change behavior; the application must decide which
cost matters more. Distinguish saved historical results from a new rerun, which may differ.

Before recommending fine-tuning, ask for the ideal inspection case, acceptable physical
tolerance, missing positive and negative examples, nuisance variation, and a held-out
test that represents the real workflow.

## Guardrails

- Never expose, print, copy into Git, or include the NGC key in evidence.
- Never expose, print, persist, or copy a SharePoint fallback link into Git or evidence.
- Never expose, print, persist, or copy the private data GitHub token into evidence.
- Never add private images, archives, or generated evidence to Git.
- Never run Nano and Reason2 2B together; they share GPU 0.
- Never hide incorrect verdicts, hallucinations, or Shift/Displace misses.
- Never modify the original reference/live images or expected labels.
- Ask before stopping Brev, switching model sets, or running a large batch.
