# Use the CLI

The CLI and browser app share the same dataset index, contour pipeline, prompts, NIM
clients, parser, and metric functions. Use it as a toolbox for questions raised during
the workshop.

## Check readiness and discover cases

```bash
./vision-inspect status
./vision-inspect pairs --collection round1
```

## Compare model reasoning and contour effects

```bash
./vision-inspect inspect --pair <pair-id> \
  --models reason2-2b reason2-8b --mode both --raw \
  --output evidence/pair-comparison.json
```

Read the original responses and compare verdict, action, object, location, unsupported
claims, and uncertainty. A contour-assisted answer can improve one dimension while
regressing another.

## Look for patterns in a larger sample

```bash
./vision-inspect batch --category Shift/Displace --count 10 \
  --model reason2-8b --mode both \
  --output evidence/shift-10.json
```

The summary reports verdict metrics, action/item grounding, NIM latency, contour
preprocessing latency, and total latency. Precision exposes false-alarm behavior; recall
exposes missed-change behavior. The intended workflow must decide which cost matters
more. Inspect individual raw rows before drawing a conclusion.

## Explore one cue hypothesis

```bash
./vision-inspect sweep --pair <pair-id> --model reason2-8b \
  --diff-methods color channel-max edges \
  --thresholds 15 25 35 --min-areas 3000 \
  --output evidence/cue-sweep.json
```

Use `--diff-method`, `--threshold`, and `--min-area` on `inspect`, `round1`, or `batch`
when one fixed contour configuration is useful. Keep comparisons matched and explain
whether a cue changed real physical grounding or merely changed the answer.

## Before fine-tuning

Use the evidence to define the intended inspection case, acceptable physical tolerance,
false-positive/false-negative trade-off, missing object/action/nuisance coverage, and an
untouched held-out test. Do not alter dataset labels to match a model.

## Optional Nano

Nano shares GPU 0 with Reason2 2B and is off by default. Switch the model set only when
the optional comparison is explicitly requested:

```bash
./scripts/select-model-set.sh nano
./vision-inspect status

./scripts/select-model-set.sh reason2
```

Reason2 8B remains available on GPU 1 during either model set.
