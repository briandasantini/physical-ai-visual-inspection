from __future__ import annotations


TUTORIAL_STEPS = [
    "Reason2 8B is green",
    "Round 1 expectations recorded",
    "Round 1 baseline completed",
    "Baseline reasoning reviewed",
    "Larger-set baseline completed",
    "Matched contour rerun completed",
    "Weakest category identified",
    "Agent cue experiment exported",
]


WORKSHOP_LOOP = (
    "Write the expected PASS/FAIL result → run the model → judge the verdict and "
    "explanation → save the evidence."
)


PHASES = [
    (
        "1 · First examples",
        "Compare models on the curated examples, then inspect a matched default-contour rerun.",
        "25 minutes",
    ),
    (
        "2 · Larger set",
        "Run a labeled sample twice. Compare verdict, action, item, and latency metrics plus raw misses.",
        "35 minutes",
    ),
    (
        "3 · Agent experiment",
        "Use the terminal agent to vary one pixel-cue method or parameter and interpret the evidence.",
        "30 minutes",
    ),
]


def progress_summary(completed: list[str] | None) -> str:
    completed = completed or []
    count = sum(step in completed for step in TUTORIAL_STEPS)
    percent = round((count / len(TUTORIAL_STEPS)) * 100)
    next_step = next((step for step in TUTORIAL_STEPS if step not in completed), None)
    if next_step is None:
        return (
            "### ✅ Tutorial complete\n"
            "The required exercises are finished. Confirm the decision, owners, and next gate."
        )
    return (
        f"### Progress: {count}/{len(TUTORIAL_STEPS)} ({percent}%)\n"
        f"**Next required gate:** {next_step}"
    )
