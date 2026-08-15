# 4. Explore

After the required three passes, design one controlled experiment. The purpose is to
turn an observed weakness into a testable data or modeling question.

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
- contour threshold.

Write the expected result before inference, then run baseline and contour-assisted modes.

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
