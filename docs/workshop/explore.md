# 3. Agent Experiment Lab

Use the embedded terminal to turn an observed weakness into a reproducible cue-generation
experiment. Ask Codex or Claude to explain the planned command before running it.

## Pick one hypothesis

Examples:

- Low-contrast changes are missed more often than high-contrast changes.
- A small displacement becomes detectable above a measurable pixel distance.
- Contours improve localization but increase false alarms under illumination changes.
- The smaller model reaches the right verdict but grounds explanations less reliably.

## Change one variable

Keep the camera, framing, and surrounding workspace fixed. Change only one factor:

- object presence;
- object position;
- orientation;
- contrast;
- illumination;
- contour difference method;
- contour threshold;
- minimum contour area.

Keep the model and inspection prompt fixed. Start with:

```bash
./vision-inspect pairs --collection round1
./vision-inspect sweep --pair <pair-id> --model reason2-8b \
  --diff-methods color channel-max edges \
  --thresholds 15 25 35 --min-areas 3000 \
  --output evidence/cue-sweep.json
```

Compare verdict correctness, action correctness, item correctness, contour regions,
changed-pixel ratio, preprocessing latency, NIM latency, and total latency.

## Turn the result into a data plan

For a persistent failure, specify:

1. the target model;
2. the failure category;
3. the missing positive and negative examples;
4. the required labels for verdict and explanation grounding;
5. nuisance variation such as lighting, camera, and background;
6. the held-out evaluation needed to prove improvement.

Post-training is justified when a stable, important failure remains after input,
prompting, and conventional vision controls have been tested.
