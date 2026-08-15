# Visual inspection CLI

The CLI and browser app call the same dataset index, contour pipeline, prompts, NIM
clients, response parser, and metric functions. Run these commands from the repository
directory on Brev. Paths passed to `--output` are copied from the application container
into the current Brev workspace directory.

## Check readiness

```bash
./vision-inspect status
```

## Follow the workshop

```bash
# See the curated first examples.
./vision-inspect pairs --collection round1

# Compare baseline and contour reasoning for one pair.
./vision-inspect inspect --pair <pair-id> --mode both --raw \
  --output evidence/pair-baseline-and-contour.json

# Run all five with 8B, baseline first.
./vision-inspect round1 --models reason2-8b --mode baseline \
  --output evidence/round1-baseline.json

# Rerun the same five with contours.
./vision-inspect round1 --models reason2-8b --mode contour \
  --output evidence/round1-contour.json

# Compare 2B and 8B on one labeled pair.
./vision-inspect inspect --pair <pair-id> \
  --models reason2-2b reason2-8b --mode both --raw

# Run the same larger-set sample in both modes and compare metrics.
./vision-inspect batch --category Shift/Displace --count 10 \
  --model reason2-8b --mode both \
  --output evidence/shift-10.json
```

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
