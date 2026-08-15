# Physical AI Visual Inspection Workshop

Learn how a vision-language model reasons about physical differences between an
**expected workspace** and an **observed workspace**.

You will begin with obvious changes, expand to a larger labeled set, and then rerun the
same evidence with OpenCV contour cues. The goal is not to prove that one technique
always wins. The goal is to discover **where the model reasons well, where it fails, and
what evidence or post-training might improve it**.

<div class="grid cards" markdown>

-   **1 · Compare**

    Run expected and observed images without extra visual guidance.

-   **2 · Evaluate**

    Judge the PASS/FAIL verdict and the explanation as separate outputs.

-   **3 · Guide**

    Add contour cues and rerun the exact same image pairs.

-   **4 · Decide**

    Identify remaining gaps and the data needed for improvement.

</div>

## The repeated loop

1. Read the labeled pair.
2. Write your expected `PASS` or `FAIL` result **before inference**.
3. Run the model.
4. Judge verdict correctness and explanation grounding separately.
5. Save the evidence.
6. Change one input and repeat on the same pair.

!!! warning "Safety boundary"
    This workshop evaluates model behavior. A model `PASS` is never authorization to
    release an automated or robotic run.

## Choose your path

=== "Browser workshop"

    Use the Brev **Open Visual Inspection** secure link. Everything required for the
    normal hands-on flow is available in the participant website.

=== "Terminal"

    Run `./vision-inspect status`, then follow the commands in the
    [CLI guide](cli.md).

=== "Coding agent"

    Open a terminal inside Brev and start `codex` or `claude`. The repository provides
    the workshop skill and safety instructions automatically.

[Launch and connect](launch.md){ .launch-button }

## What success looks like

By the end, your evidence should answer:

- Which change categories are reliably detected?
- When is the verdict correct but the explanation unsupported?
- Do contour cues improve grounding, introduce false alarms, or have no effect?
- Which failures require conventional vision controls, better prompts, or post-training?
- What labeled examples should be collected next?
