from __future__ import annotations

import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

import gradio as gr
from PIL import Image

from .config import MODELS, default_model_label, model_from_label, model_labels
from .datasets import InspectionPair, build_index, filter_pairs
from .evaluation import calculate_metrics, metrics_row
from .nim_client import health_status, inspect_workspace
from .tutorial import (
    PHASES,
    TUTORIAL_STEPS,
    WORKSHOP_LOOP,
    progress_summary,
)
from .vision import build_contour_diff


CSS = """
.gradio-container { max-width: 1480px !important; }
.hero { border-left: 6px solid #76b900; padding-left: 18px; }
.safety-note { background: #fff6d8; border: 1px solid #e4bf4a; padding: 12px; border-radius: 8px; }
.status-card { border: 1px solid #d8d8d8; padding: 10px 14px; border-radius: 8px; }
.guide-card { border: 1px solid #d8d8d8; border-radius: 10px; padding: 10px 16px; min-height: 160px; }
.guide-card h3 { color: #3b5f00; }
.tutorial-progress { border-left: 6px solid #76b900; padding: 4px 16px; margin: 8px 0 16px; }
"""


DATA_ROOT = os.getenv("VISUAL_INSPECTION_DATA_ROOT", "/data")
DATA_PROFILE = os.getenv("VISUAL_INSPECTION_DATA_PROFILE", "workshop")
DATA_VERSION = os.getenv("VISUAL_INSPECTION_DATA_VERSION", "unknown")
DOCS_URL = os.getenv(
    "VISUAL_INSPECTION_DOCS_URL",
    "https://briandasantini.github.io/physical-ai-visual-inspection/",
).strip()
TABLE_HEADERS = ["Pair ID", "Collection", "Category", "Expected", "Scene", "Error"]
RESULT_HEADERS = [
    "Model",
    "Input",
    "Expected",
    "Verdict",
    "Correct?",
    "Confidence",
    "Latency (s)",
    "Issue",
]
BATCH_HEADERS = [
    "Pair",
    "Category",
    "Expected",
    "Verdict",
    "Correct?",
    "Confidence",
    "Issue",
]


def _index() -> tuple[InspectionPair, ...]:
    return build_index(DATA_ROOT)


def _round_one_pairs() -> list[InspectionPair]:
    exact = [pair for pair in _index() if pair.collection == "Round 1"]
    if exact:
        return exact[:5]
    return [pair for pair in _index() if pair.collection == "Workshop pairs"][:5]


def _pair_choices(pairs: list[InspectionPair]) -> list[tuple[str, str]]:
    return [
        (
            f"{pair.scene} · {pair.error_type} · expected {pair.expected}",
            pair.pair_id,
        )
        for pair in pairs
    ]


def _status_markdown() -> str:
    lines = ["### Model status"]
    for model in MODELS.values():
        ready, detail = health_status(model)
        if ready:
            lines.append(f"- 🟢 **{model.label}:** Ready")
        elif model.optional:
            lines.append(f"- ⚪ **{model.label}:** Off — facilitator can activate it")
        else:
            lines.append(f"- 🟡 **{model.label}:** Starting — `{detail[:100]}`")
    return "\n".join(lines)


def _verdict_markdown(result: dict) -> str:
    verdict = result["verdict"]
    icon = "✅" if verdict == "PASS" else "⛔" if verdict == "FAIL" else "⚠️"
    return (
        f"## {icon} {verdict}\n"
        f"**Confidence:** {result['confidence']}  \n"
        f"**Issue:** {result['issues']}  \n"
        f"**Model:** {result['model']} · **Input:** {result['analysis_mode']} · "
        f"**Latency:** {result['latency_seconds']:.2f}s"
    )


def _reasoning_markdown(results: list[dict], unavailable: list[str]) -> str:
    sections = []
    if unavailable:
        sections.append(f"> Skipped because not running: {', '.join(unavailable)}")
    for result in results:
        sections.append(
            f"### {result['model']} · {result['analysis_mode']}\n"
            f"**{result['verdict']} / {result['confidence']}** — {result['issues']}\n\n"
            f"```text\n{result['raw_response']}\n```"
        )
    return "\n\n".join(sections) or "No model was available."


def _result_rows(results: list[dict], expected: str) -> list[list]:
    return [
        [
            result["model"],
            result["analysis_mode"],
            expected,
            result["verdict"],
            "Yes" if result["verdict"] == expected else "No",
            result["confidence"],
            result["latency_seconds"],
            result["issues"],
        ]
        for result in results
    ]


def _run_selected_models(
    reference: Image.Image,
    live: Image.Image,
    selected_labels: list[str],
    mode: str,
) -> tuple[list[dict], list[str], Image.Image]:
    if not selected_labels:
        raise gr.Error("Select at least one model.")
    contour = build_contour_diff(reference, live)
    selected = [model_from_label(label) for label in selected_labels]
    ready_models = []
    unavailable = []
    for model in selected:
        if health_status(model)[0]:
            ready_models.append(model)
        else:
            unavailable.append(model.label)
    if not ready_models:
        raise gr.Error("None of the selected models is running yet.")

    inference_contour = contour if mode == "Contour-assisted" else None
    with ThreadPoolExecutor(max_workers=len(ready_models)) as executor:
        inspections = list(
            executor.map(
                lambda selected_model: inspect_workspace(
                    reference,
                    live,
                    inference_contour,
                    selected_model,
                ),
                ready_models,
            )
        )
    return [inspection.to_dict() for inspection in inspections], unavailable, contour.image


def run_workshop_comparison(
    reference: Image.Image | None,
    live: Image.Image | None,
    expected: str,
    selected_labels: list[str],
    mode: str,
    pair_id: str = "custom",
):
    if reference is None or live is None:
        raise gr.Error("Load or upload both images first.")
    expected = expected.strip().upper()
    if expected not in {"PASS", "FAIL"}:
        raise gr.Error("Record the expected result as PASS or FAIL before inference.")
    results, unavailable, contour_image = _run_selected_models(
        reference,
        live,
        selected_labels,
        mode,
    )
    evidence = {
        "pair_id": pair_id,
        "expected": expected,
        "mode": mode,
        "unavailable": unavailable,
        "results": results,
    }
    return (
        contour_image,
        _result_rows(results, expected),
        _reasoning_markdown(results, unavailable),
        evidence,
    )


def compare_pair_runs(baseline: dict | None, contour: dict | None):
    if not baseline or not contour:
        raise gr.Error("Run both baseline and contour-assisted comparisons first.")
    if baseline.get("pair_id") != contour.get("pair_id"):
        raise gr.Error("The two runs used different pairs. Rerun both on the same pair.")
    baseline_by_model = {item["model"]: item for item in baseline["results"]}
    contour_by_model = {item["model"]: item for item in contour["results"]}
    rows = []
    for model in sorted(set(baseline_by_model) | set(contour_by_model)):
        before = baseline_by_model.get(model, {})
        after = contour_by_model.get(model, {})
        rows.append(
            [
                model,
                before.get("verdict", "—"),
                after.get("verdict", "—"),
                before.get("issues", "—"),
                after.get("issues", "—"),
            ]
        )
    return rows


def run_inspection(
    reference: Image.Image | None,
    live: Image.Image | None,
    model_label: str,
    mode: str,
):
    if reference is None or live is None:
        raise gr.Error("Add both a reference image and a live image.")
    model = model_from_label(model_label)
    ready, detail = health_status(model)
    if not ready:
        raise gr.Error(f"{model.label} is not running: {detail}")
    contour = build_contour_diff(reference, live)
    result = inspect_workspace(
        reference,
        live,
        contour if mode == "Contour-assisted" else None,
        model,
    )
    result_dict = result.to_dict()
    return contour.image, _verdict_markdown(result_dict), result.raw_response, result_dict


def run_batch(category: str, sample_count: int, model_label: str, mode: str):
    model = model_from_label(model_label)
    ready, detail = health_status(model)
    if not ready:
        raise gr.Error(f"{model.label} is not running: {detail}")

    candidates = [
        pair
        for pair in _index()
        if pair.collection not in {"Round 1", "Workshop pairs"}
        and (category == "All" or pair.category == category)
    ]
    selected = candidates[: int(sample_count)]
    if not selected:
        raise gr.Error("No larger-set pairs match this category in the active data profile.")

    records = []
    for pair in selected:
        reference = Image.open(pair.reference).convert("RGB")
        live = Image.open(pair.live).convert("RGB")
        contour = build_contour_diff(reference, live)
        result = inspect_workspace(
            reference,
            live,
            contour if mode == "Contour-assisted" else None,
            model,
        ).to_dict()
        records.append({**pair.to_dict(), **result})

    metrics = calculate_metrics(records)
    summary = (
        f"### {mode}: {metrics['correct']}/{metrics['pairs']} correct\n"
        f"**Accuracy:** {metrics['accuracy']:.0%} · **Precision:** {metrics['precision']:.0%} · "
        f"**Recall:** {metrics['recall']:.0%} · **F1:** {metrics['f1']:.0%}"
    )
    rows = [
        [
            record["pair_id"],
            record["category"],
            record["expected"],
            record["verdict"],
            "Yes" if record["expected"] == record["verdict"] else "No",
            record["confidence"],
            record["issues"],
        ]
        for record in records
    ]
    evidence = {
        "category": category,
        "sample_count": len(selected),
        "model": model.label,
        "mode": mode,
        "metrics": metrics,
        "records": records,
    }
    return summary, rows, evidence


def compare_batch_runs(baseline: dict | None, contour: dict | None):
    if not baseline or not contour:
        raise gr.Error("Run both larger-set passes first.")
    baseline_ids = [record["pair_id"] for record in baseline["records"]]
    contour_ids = [record["pair_id"] for record in contour["records"]]
    if baseline_ids != contour_ids:
        raise gr.Error("The two runs used different pairs. Rerun them with matching settings.")
    if baseline.get("model") != contour.get("model"):
        raise gr.Error("The two runs used different models. Rerun them with one model.")
    return [
        metrics_row("Baseline", baseline["metrics"]),
        metrics_row("Contour-assisted", contour["metrics"]),
    ]


def export_result(result: dict | None) -> str:
    if not result:
        raise gr.Error("Run an exercise before exporting.")
    file_handle = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        prefix="visual-inspection-result-",
        delete=False,
    )
    with file_handle:
        json.dump(result, file_handle, indent=2)
        file_handle.write("\n")
    return file_handle.name


def dataset_summary() -> str:
    pairs = _index()
    counts: dict[str, int] = {}
    for pair in pairs:
        counts[pair.category] = counts.get(pair.category, 0) + 1
    count_text = " · ".join(
        f"**{category}:** {count}" for category, count in sorted(counts.items())
    )
    return f"**Indexed pairs:** {len(pairs)}  \n{count_text or 'Data is still loading.'}"


def search_dataset(category: str, query: str):
    matches = filter_pairs(_index(), category=category, query=query)
    choices = _pair_choices(matches)
    value = choices[0][1] if choices else None
    return [pair.to_row() for pair in matches], gr.Dropdown(choices=choices, value=value)


def load_pair(pair_id: str):
    pair = next((item for item in _index() if item.pair_id == pair_id), None)
    if pair is None:
        raise gr.Error("Select a dataset pair first.")
    return (
        Image.open(pair.reference).convert("RGB"),
        Image.open(pair.live).convert("RGB"),
        pair.expected,
        pair.to_dict(),
    )


def build_demo() -> gr.Blocks:
    round_one = _round_one_pairs()
    round_one_choices = _pair_choices(round_one)
    all_pairs = list(_index())
    all_choices = _pair_choices(all_pairs[:200])

    with gr.Blocks(title="Physical AI Visual Inspection") as demo:
        gr.Markdown(
            f"""<div class="hero">

# Physical AI Visual Inspection Workshop
### Establish a baseline, inspect the misses, then add visual guidance

**The loop:** {WORKSHOP_LOOP}

[Open the full workshop guide]({DOCS_URL})

</div>"""
        )

        status = gr.Markdown(_status_markdown(), elem_classes=["status-card"])
        refresh_status = gr.Button("Refresh model status", size="sm")
        refresh_status.click(_status_markdown, outputs=status)

        with gr.Tabs():
            with gr.Tab("Workshop Guide"):
                gr.Markdown(
                    f"""
## One workshop, three passes

The environment contains the app, pinned dataset **{DATA_PROFILE}/{DATA_VERSION}**, and
the model services. Participants stay in this website; a facilitator only uses the
terminal to activate optional Nano.
"""
                )
                gr.Markdown(
                    """
## Optional: use Cursor, VS Code, Codex, or Claude

The website is enough for the workshop. If you want an agent working directly in Brev,
run one of these commands from a **terminal on your laptop**:

```bash
brev open <instance-name> code --dir /home/nvidia/workspace/physical-ai-visual-inspection/physical-ai-visual-inspection
brev open <instance-name> cursor --dir /home/nvidia/workspace/physical-ai-visual-inspection/physical-ai-visual-inspection
```

In the remote editor terminal, run `./vision-inspect status`, then use the editor's agent or
start `codex` or `claude`. Read `REMOTE_EDITORS.md` in the repository for prerequisites
and troubleshooting. Closing the editor does **not** stop the paid Brev instance.
"""
                )
                with gr.Row(equal_height=True):
                    for title, description, duration in PHASES:
                        gr.Markdown(
                            f"### {title}\n{description}\n\n**Time:** {duration}",
                            elem_classes=["guide-card"],
                        )

                gr.Markdown("## Follow these steps")
                tutorial_progress = gr.Markdown(
                    progress_summary([]),
                    elem_classes=["tutorial-progress"],
                )
                tutorial_checklist = gr.CheckboxGroup(
                    choices=TUTORIAL_STEPS,
                    label="Workshop evidence checklist",
                )
                tutorial_checklist.change(
                    progress_summary,
                    inputs=tutorial_checklist,
                    outputs=tutorial_progress,
                )

                with gr.Accordion("Optional Cosmos3 Nano", open=False):
                    gr.Markdown(
                        "Nano is installed but stopped, so it uses no GPU. It shares GPU 0 "
                        "with Reason2 2B; the facilitator can switch between them with "
                        "`./scripts/select-model-set.sh nano` or "
                        "`./scripts/select-model-set.sh reason2`. Reason2 8B stays on GPU 1."
                    )

            with gr.Tab("1 · First Examples"):
                gr.Markdown(
                    """
## Start with the curated examples

1. Load one labeled pair and read the expected result.
2. Run **Baseline**: models see only reference + live.
3. Read the raw reasoning. Mark correct details, misses, and hallucinations.
4. Repeat for all five examples before adding contours.
5. Run **Contour-assisted** on the same pair and compare what changed.
"""
                )
                with gr.Row():
                    round_choice = gr.Dropdown(
                        choices=round_one_choices,
                        value=round_one_choices[0][1] if round_one_choices else None,
                        label="Round 1 pair",
                        scale=4,
                    )
                    load_round = gr.Button("Load pair", variant="secondary", scale=1)
                with gr.Row():
                    round_reference = gr.Image(label="Reference", type="pil", height=340)
                    round_live = gr.Image(label="Live", type="pil", height=340)
                    round_contour = gr.Image(
                        label="Contour view (not sent during baseline)",
                        type="pil",
                        height=340,
                        interactive=False,
                    )
                with gr.Row():
                    round_expected = gr.Textbox(
                        label="Expected result — record before running",
                        placeholder="PASS or FAIL",
                    )
                    round_models = gr.CheckboxGroup(
                        choices=model_labels(),
                        value=[MODELS["reason2-8b"].label, MODELS["reason2-2b"].label],
                        label="Models to compare",
                    )
                round_metadata = gr.JSON(label="Pair metadata", visible=False)
                load_round.click(
                    load_pair,
                    inputs=round_choice,
                    outputs=[round_reference, round_live, round_expected, round_metadata],
                )

                with gr.Row():
                    run_baseline = gr.Button("A · Run baseline", variant="primary")
                    run_contour = gr.Button("B · Run with contours", variant="secondary")

                baseline_state = gr.State()
                contour_state = gr.State()
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Baseline results")
                        baseline_table = gr.Dataframe(headers=RESULT_HEADERS, interactive=False)
                        baseline_reasoning = gr.Markdown()
                    with gr.Column():
                        gr.Markdown("### Contour-assisted results")
                        contour_table = gr.Dataframe(headers=RESULT_HEADERS, interactive=False)
                        contour_reasoning = gr.Markdown()

                run_baseline.click(
                    lambda reference, live, expected, models, pair_id: run_workshop_comparison(
                        reference, live, expected, models, "Baseline", pair_id
                    ),
                    inputs=[
                        round_reference,
                        round_live,
                        round_expected,
                        round_models,
                        round_choice,
                    ],
                    outputs=[round_contour, baseline_table, baseline_reasoning, baseline_state],
                )
                run_contour.click(
                    lambda reference, live, expected, models, pair_id: run_workshop_comparison(
                        reference, live, expected, models, "Contour-assisted", pair_id
                    ),
                    inputs=[
                        round_reference,
                        round_live,
                        round_expected,
                        round_models,
                        round_choice,
                    ],
                    outputs=[round_contour, contour_table, contour_reasoning, contour_state],
                )

                compare_pair_button = gr.Button("Compare baseline vs contour reasoning")
                pair_comparison = gr.Dataframe(
                    headers=[
                        "Model",
                        "Baseline verdict",
                        "Contour verdict",
                        "Baseline explanation",
                        "Contour explanation",
                    ],
                    interactive=False,
                )
                compare_pair_button.click(
                    compare_pair_runs,
                    inputs=[baseline_state, contour_state],
                    outputs=pair_comparison,
                )
                with gr.Row():
                    download_baseline = gr.DownloadButton("Download baseline JSON")
                    download_contour = gr.DownloadButton("Download contour JSON")
                download_baseline.click(export_result, inputs=baseline_state, outputs=download_baseline)
                download_contour.click(export_result, inputs=contour_state, outputs=download_contour)

            with gr.Tab("2 · Larger Set"):
                gr.Markdown(
                    """
## Check whether the first five examples generalize

Choose a category and sample size. Run baseline first, then rerun the **same ordered
pairs** with contours. Ten pairs can take several minutes. Inspect every incorrect row;
the aggregate score alone is not the workshop finding.
"""
                )
                with gr.Row():
                    batch_category = gr.Dropdown(
                        choices=[
                            "All",
                            "Add",
                            "Remove",
                            "Replace/Swap",
                            "Shift/Displace",
                            "Illumination",
                            "PASS",
                            "Other",
                        ],
                        value="All",
                        label="Category",
                    )
                    batch_count = gr.Slider(3, 20, value=10, step=1, label="Pairs")
                    batch_model = gr.Dropdown(
                        choices=model_labels(),
                        value=default_model_label(),
                        label="Model",
                    )
                with gr.Row():
                    batch_baseline_button = gr.Button("A · Run larger-set baseline", variant="primary")
                    batch_contour_button = gr.Button("B · Rerun same set with contours")

                batch_baseline_state = gr.State()
                batch_contour_state = gr.State()
                with gr.Row():
                    with gr.Column():
                        batch_baseline_summary = gr.Markdown("Baseline not run yet.")
                        batch_baseline_table = gr.Dataframe(headers=BATCH_HEADERS, interactive=False)
                    with gr.Column():
                        batch_contour_summary = gr.Markdown("Contour rerun not run yet.")
                        batch_contour_table = gr.Dataframe(headers=BATCH_HEADERS, interactive=False)
                batch_baseline_button.click(
                    lambda category, count, model: run_batch(category, count, model, "Baseline"),
                    inputs=[batch_category, batch_count, batch_model],
                    outputs=[batch_baseline_summary, batch_baseline_table, batch_baseline_state],
                )
                batch_contour_button.click(
                    lambda category, count, model: run_batch(
                        category, count, model, "Contour-assisted"
                    ),
                    inputs=[batch_category, batch_count, batch_model],
                    outputs=[batch_contour_summary, batch_contour_table, batch_contour_state],
                )
                compare_batch_button = gr.Button("C · Compare larger-set metrics", variant="primary")
                batch_comparison = gr.Dataframe(
                    headers=["Run", "Pairs", "Accuracy", "Precision", "Recall", "F1"],
                    interactive=False,
                )
                compare_batch_button.click(
                    compare_batch_runs,
                    inputs=[batch_baseline_state, batch_contour_state],
                    outputs=batch_comparison,
                )
                with gr.Row():
                    download_batch_baseline = gr.DownloadButton("Download baseline evidence")
                    download_batch_contour = gr.DownloadButton("Download contour evidence")
                download_batch_baseline.click(
                    export_result,
                    inputs=batch_baseline_state,
                    outputs=download_batch_baseline,
                )
                download_batch_contour.click(
                    export_result,
                    inputs=batch_contour_state,
                    outputs=download_batch_contour,
                )

            with gr.Tab("3 · Explore"):
                gr.Markdown(
                    """
## Apply the same loop to a new hypothesis

Upload a controlled workspace image pair or load any indexed pair. Change one variable at a
time, write the expected result first, and test baseline before contour assistance.
Prioritize small shifts because they were the weakest historical category.
"""
                )
                with gr.Row():
                    reference = gr.Image(label="Expected workspace", type="pil", height=360)
                    live = gr.Image(label="Observed workspace", type="pil", height=360)
                    contour_view = gr.Image(
                        label="Contour-assisted view",
                        type="pil",
                        height=360,
                        interactive=False,
                    )
                with gr.Row():
                    model = gr.Dropdown(
                        choices=model_labels(),
                        value=default_model_label(),
                        label="NIM",
                    )
                    explore_mode = gr.Radio(
                        choices=["Baseline", "Contour-assisted"],
                        value="Baseline",
                        label="Input mode",
                    )
                    inspect_button = gr.Button("Inspect workspace", variant="primary")
                verdict = gr.Markdown("## Waiting for inspection")
                with gr.Accordion("Reasoning and evidence", open=True):
                    raw = gr.Textbox(label="Raw NIM response", lines=12)
                    structured = gr.JSON(label="Structured result")
                    download_inspection = gr.DownloadButton("Download JSON")
                inspect_button.click(
                    run_inspection,
                    inputs=[reference, live, model, explore_mode],
                    outputs=[contour_view, verdict, raw, structured],
                )
                download_inspection.click(export_result, inputs=structured, outputs=download_inspection)

                with gr.Accordion("Load from the organized dataset", open=False):
                    gr.Markdown(dataset_summary())
                    with gr.Row():
                        category = gr.Dropdown(
                            choices=[
                                "All",
                                "Add",
                                "Remove",
                                "Replace/Swap",
                                "Shift/Displace",
                                "Illumination",
                                "PASS",
                                "Curated",
                                "Other",
                            ],
                            value="All",
                            label="Category",
                        )
                        query = gr.Textbox(label="Scene or error search")
                        search_button = gr.Button("Search")
                    pair_table = gr.Dataframe(
                        value=[pair.to_row() for pair in all_pairs[:200]],
                        headers=TABLE_HEADERS,
                        interactive=False,
                    )
                    pair_choice = gr.Dropdown(
                        choices=all_choices,
                        value=all_choices[0][1] if all_choices else None,
                        label="Pair to load",
                    )
                    load_button = gr.Button("Load pair", variant="primary")
                    selected_expected = gr.Textbox(label="Expected result")
                    selected_metadata = gr.JSON(label="Selected pair metadata")
                    search_button.click(
                        search_dataset,
                        inputs=[category, query],
                        outputs=[pair_table, pair_choice],
                    )
                    load_button.click(
                        load_pair,
                        inputs=pair_choice,
                        outputs=[reference, live, selected_expected, selected_metadata],
                    )

        gr.Markdown(
            """<div class="safety-note">

**Workshop system — not a production safety interlock.** A PASS result must not release
an automated run without independently validated controls. Explanations can sound persuasive
while being wrong; judge them against the labeled image pair.

</div>"""
        )

    return demo


if __name__ == "__main__":
    build_demo().queue(default_concurrency_limit=2).launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        css=CSS,
    )
