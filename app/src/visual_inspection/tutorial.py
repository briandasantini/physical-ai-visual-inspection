from __future__ import annotations


TUTORIAL_STEPS = [
    "Reason2 8B is green",
    "Round 1 expectations recorded",
    "Round 1 baseline completed",
    "Baseline reasoning reviewed",
    "Larger-set baseline completed",
    "Contour-assisted rerun completed",
    "Weakest category identified",
    "Evidence exported and finding recorded",
]


WORKSHOP_LOOP = (
    "Write the expected PASS/FAIL result → run the model → judge the verdict and "
    "explanation → save the evidence."
)


PHASES = [
    (
        "1 · First examples",
        "Run the curated first examples without contours. Compare verdicts and reasoning across available models.",
        "25 minutes",
    ),
    (
        "2 · Larger set",
        "Run a labeled sample from the larger evaluation set. Compare category metrics, misses, and false alarms.",
        "35 minutes",
    ),
    (
        "3 · Add contours",
        "Rerun the exact same examples with contour hints. Compare both the scores and the model reasoning.",
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
