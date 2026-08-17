# Physical AI Visual Inspection Workshop

Explore how vision-language models reason about physical differences between an
**expected workspace** and an **observed workspace**—and define what useful visual
inspection would mean for your application.

This is not a PASS/FAIL certification or a model leaderboard. The models will be right,
wrong, uncertain, and occasionally convincing for the wrong reason. Those behaviors are
the material for the workshop.

<div class="grid cards" markdown>

-   **1 · Observe**

    Find where 2B and 8B see the real change, miss it, or hallucinate one.

-   **2 · Compare**

    Separate verdict quality from action, object, location, and contour effects.

-   **3 · Define**

    Discuss tolerances, false alarms versus missed changes, and the ideal use case.

-   **4 · Discover gaps**

    Identify missing cases and the data needed before fine-tuning.

</div>

## The working loop

1. Choose a question about the model or intended inspection workflow.
2. Inspect a few labeled cases and read the original model responses.
3. Separate verdict, action, object, location, uncertainty, and unsupported claims.
4. Compare the same cases across models or with and without contour cues.
5. Look for a pattern and a case that contradicts it.
6. Turn the finding into a requirement, missing-case list, or next experiment.

Dataset labels are reference annotations. You do not need to predict or retype them. If a
label or image seems ambiguous, that is a data-quality finding worth discussing.

## Questions to carry through the workshop

- Where is each model useful, and where does it hallucinate or miss changes?
- Do contours improve detection while degrading action or object understanding?
- Which false positives or false negatives are more costly for the real workflow?
- What amount of displacement, angle, occupancy, or object variation should be tolerated?
- Are important objects, actions, nuisance conditions, or edge cases missing?
- What would an ideal inspection case look like?
- What positive, negative, nuisance, and held-out data would be necessary for fine-tuning?

## Choose your path

=== "Browser workshop"

    Use the Brev **Open Visual Inspection** secure link for the guided controls.

=== "Terminal"

    Run `./vision-inspect status`, then use the [CLI guide](cli.md) as a question-driven
    toolbox.

=== "Codex/Claude"

    In **3 · Explore**, open the Jupyter terminal and ask an agent to investigate one
    question about reasoning, contours, tolerances, missing cases, or data.

[Launch and connect](launch.md){ .launch-button }

## A useful outcome

The workshop should leave the team with a clearer operating hypothesis—not a polished
score: observed strengths and failure modes, the important error trade-off, a physical
tolerance to investigate, missing cases, and an evidence-backed next step.
