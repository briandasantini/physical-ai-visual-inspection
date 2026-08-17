# Visual inspection CLI

The CLI and browser app call the same dataset index, contour pipeline, prompts, NIM
clients, response parser, and metric functions. Run these commands from the repository
directory on Brev. Paths passed to `--output` are copied from the application container
into the current Brev workspace directory.

The CLI is a toolbox for workshop questions, not a requirement to optimize one score.
Use dataset labels as reference annotations, preserve raw responses, and ask what each
result means for the intended inspection workflow.

## Check readiness

```bash
./vision-inspect status
```

## Explore model behavior

```bash
# Discover the curated cases and the physical changes they cover.
./vision-inspect pairs --collection round1

# See where 2B and 8B agree, disagree, miss, or hallucinate on one pair.
./vision-inspect inspect --pair <pair-id> \
  --models reason2-2b reason2-8b --mode baseline --raw \
  --output evidence/pair-model-comparison.json

# Ask whether contours change verdict, action, object, hallucination, or latency.
./vision-inspect inspect --pair <pair-id> \
  --models reason2-2b reason2-8b --mode both --raw \
  --output evidence/pair-baseline-and-contour.json

# Characterize unaided 8B behavior across the five examples.
./vision-inspect round1 --models reason2-8b --mode baseline \
  --output evidence/round1-baseline.json

# Rerun the same five with the default contour settings.
./vision-inspect round1 --models reason2-8b --mode contour \
  --output evidence/round1-contour.json
```

## Look for recurring patterns and error trade-offs

```bash
# Run a fixed sample in both modes and inspect individual rows as well as metrics.
./vision-inspect batch --category Shift/Displace --count 10 \
  --model reason2-8b --mode both \
  --output evidence/shift-10.json

# Explore whether a pixel-cue choice helps or hurts the same case.
./vision-inspect sweep --pair <pair-id> --model reason2-8b \
  --diff-methods color channel-max edges \
  --thresholds 15 25 35 --min-areas 3000 \
  --output evidence/cue-sweep.json
```

All inference commands also accept `--diff-method`, `--threshold`, and `--min-area` for
a fixed contour configuration. Batch evidence reports verdict, action, and item metrics
plus NIM, preprocessing, and total latency.

## Interpret the evidence

- **Precision** describes false-alarm behavior; **recall** describes missed-change behavior.
  Which matters more depends on the intended workflow.
- Read action and item percentages beside verdict metrics. A correct `FAIL` with the wrong
  physical explanation may not be useful.
- Inspect raw responses for hallucinated objects, unsupported locations, and uncertainty.
- Compare contour and baseline only on the same model and pairs. A cue may help the verdict
  while degrading action or object quality.
- Treat ambiguous labels and missing object/action types as data findings. Do not edit a
  label to make a model look correct.

Before proposing fine-tuning, identify the desired physical tolerance, the cost of false
positives versus false negatives, missing positive and negative cases, nuisance variation,
and a held-out test that represents the real use case.

## Optional Nano

Nano is installed but off. It shares GPU 0 with Reason2 2B:

```bash
export NGC_API_KEY="$(cat ~/.secrets/visual-inspection-ngc-key)"
./scripts/select-model-set.sh nano
./vision-inspect status
./vision-inspect inspect --pair <pair-id> --models cosmos3-nano --mode both

./scripts/select-model-set.sh reason2
```

Reason2 8B remains available on GPU 1 during either model set.
