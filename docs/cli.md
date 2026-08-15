# Use the CLI

The CLI and browser app share the same dataset index, contour pipeline, prompts, NIM
clients, parser, and metric functions.

## Check readiness

```bash
./vision-inspect status
./vision-inspect pairs --collection round1
```

## First examples

```bash
./vision-inspect round1 --models reason2-8b --mode baseline \
  --output evidence/round1-baseline.json

./vision-inspect round1 --models reason2-8b --mode contour \
  --output evidence/round1-contour.json
```

## Inspect one pair

```bash
./vision-inspect inspect --pair <pair-id> \
  --models reason2-2b reason2-8b --mode both --raw \
  --output evidence/pair-comparison.json
```

## Larger-set comparison

```bash
./vision-inspect batch --category Shift/Displace --count 10 \
  --model reason2-8b --mode both \
  --output evidence/shift-10.json
```

## Optional Nano

Nano shares GPU 0 with Reason2 2B and is off by default. Only the facilitator should
switch the model set:

```bash
./scripts/select-model-set.sh nano
./vision-inspect status

./scripts/select-model-set.sh reason2
```

Reason2 8B remains available on GPU 1 during either model set.
