from __future__ import annotations

import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

import gradio as gr
from PIL import Image

from .config import MODELS, default_model_label, model_from_label, model_labels
from .datasets import InspectionPair, build_index, filter_pairs
from .evaluation import add_semantic_scores, calculate_metrics, metrics_row
from .nim_client import health_status, inspect_workspace, prompt_bundle_for
from .tutorial import PHASES
from .vision import build_contour_diff


NVIDIA_THEME = gr.themes.Default(
    primary_hue=gr.themes.colors.gray,
    secondary_hue=gr.themes.colors.gray,
    neutral_hue=gr.themes.colors.gray,
).set(
    color_accent="#76b900",
    color_accent_soft="#f4f9e8",
    color_accent_soft_dark="#354f0b",
    border_color_accent="#76b900",
    border_color_accent_dark="#76b900",
    link_text_color="#4f7d00",
    link_text_color_dark="#94ca36",
    link_text_color_hover="#639d00",
    link_text_color_hover_dark="#b1d967",
    checkbox_background_color_selected="#76b900",
    checkbox_background_color_selected_dark="#76b900",
    checkbox_border_color_selected="#76b900",
    checkbox_border_color_selected_dark="#76b900",
    checkbox_label_background_fill_selected="#f4f9e8",
    checkbox_label_background_fill_selected_dark="#354f0b",
    checkbox_label_border_color_selected="#76b900",
    checkbox_label_border_color_selected_dark="#76b900",
    checkbox_label_text_color_selected="#3f6205",
    checkbox_label_text_color_selected_dark="#e5f2cc",
    button_primary_background_fill="#76b900",
    button_primary_background_fill_dark="#76b900",
    button_primary_background_fill_hover="#639d00",
    button_primary_background_fill_hover_dark="#94ca36",
    button_primary_border_color="#76b900",
    button_primary_border_color_dark="#76b900",
    button_primary_border_color_hover="#639d00",
    button_primary_border_color_hover_dark="#94ca36",
    button_primary_text_color="white",
    button_primary_text_color_dark="#111111",
    loader_color="#76b900",
    loader_color_dark="#94ca36",
    slider_color="#76b900",
    slider_color_dark="#94ca36",
)


CSS = """
.gradio-container { max-width: 1480px !important; }
.hero { border-left: 6px solid #76b900; padding-left: 18px; }
.status-row { align-items: center; gap: 14px; margin: 18px 0 34px; }
.status-card { border: 0 !important; padding: 0 !important; box-shadow: none !important; }
.status-actions { flex: 0 0 190px !important; max-width: 190px; }
.status-refresh { width: 100%; }
.guide-card { border: 1px solid #d8d8d8; border-radius: 10px; padding: 10px 16px; min-height: 145px; }
.guide-card .guide-card-button { margin: 0; }
.guide-card .guide-card-button button { justify-content: flex-start; padding: 4px 0 8px; color: #3b5f00; font-size: 1.5rem; font-weight: 700; text-align: left; background: transparent; border: 0; box-shadow: none; }
.guide-card .guide-card-button button:hover { color: #548600; background: transparent; }
.guide-card p { font-size: 1.08rem; line-height: 1.55; }
.guide-docs-link { margin: 0 0 18px; }
.guide-docs-link p { margin: 0; font-size: 0.95rem; line-height: 1.4; }
.guide-docs-link a,
.guide-docs-link a:visited {
    color: #6b7280 !important;
    font-weight: 500;
    text-decoration-color: #9ca3af;
    transition: color 120ms ease, text-decoration-color 120ms ease;
}
.guide-docs-link a:hover,
.guide-docs-link a:focus-visible,
.guide-docs-link a:active {
    color: #639d00 !important;
    text-decoration-color: #76b900;
}
.workshop-tabs > .tab-wrapper > .tab-container[role="tablist"] {
    margin-bottom: 18px;
}
.workshop-tabs > .tab-wrapper > .tab-container[role="tablist"] > button[role="tab"] {
    padding: 11px 16px;
    font-size: 1.12rem !important;
    font-weight: 700 !important;
}
.section-intro h2 { font-size: clamp(1.8rem, 2.25vw, 2.3rem); line-height: 1.2; }
.section-intro p, .section-intro li { font-size: 1.15rem; line-height: 1.6; }
@media (max-width: 760px) {
    .status-row { margin-bottom: 24px; }
    .status-actions { flex: 1 1 100% !important; max-width: none; }
    .workshop-tabs > .tab-wrapper > .tab-container[role="tablist"] > button[role="tab"] {
        padding: 9px 10px;
        font-size: 1rem !important;
    }
}
"""


DATA_ROOT = os.getenv("VISUAL_INSPECTION_DATA_ROOT", "/data")
DOCS_REVISION = os.getenv(
    "VISUAL_INSPECTION_DOCS_REVISION",
    "20260817-start-here-v3",
).strip()


def _docs_url() -> str:
    base_url = os.getenv(
        "VISUAL_INSPECTION_DOCS_URL",
        "https://briandasantini.github.io/physical-ai-visual-inspection/",
    ).strip()
    if not DOCS_REVISION:
        return base_url
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}v={DOCS_REVISION}"


DOCS_URL = _docs_url()


def _jupyter_url() -> str:
    explicit_url = os.getenv("VISUAL_INSPECTION_JUPYTER_URL", "").strip()
    if explicit_url:
        return explicit_url
    brev_environment_id = os.getenv("BREV_ENV_ID", "").strip()
    if brev_environment_id:
        return f"https://jupyter-{brev_environment_id}.apps.run.brev.nvidia.com/lab"
    return ""


JUPYTER_URL = _jupyter_url()

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
    "Expected action",
    "Action correct?",
    "Expected object",
    "Object correct?",
    "Confidence",
    "Issue",
]
BATCH_COMPARISON_HEADERS = [
    "Run",
    "Pairs",
    "Accuracy",
    "Precision",
    "Recall",
    "F1",
    "Action %",
    "Object/item %",
    "Avg NIM",
    "Avg preprocessing",
    "Avg total",
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
            lines.append(f"- ⚪ **{model.label}:** Off — optional model")
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
        section = (
            f"### {result['model']} · {result['analysis_mode']}\n"
            f"**Scored result:** {result['verdict']} / {result['confidence']} — "
            f"{result['issues']}\n\n"
            f"**Original selected model response**\n\n"
            f"```text\n{result['raw_response']}\n```"
        )
        normalized = result.get("normalized_response", result["raw_response"])
        if normalized.strip() != result["raw_response"].strip():
            section += (
                "\n\n<details><summary>Normalized response used for scoring</summary>\n\n"
                f"```text\n{normalized}\n```\n"
                "</details>"
            )
        sections.append(section)
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
        raise gr.Error("This comparison needs a labeled PASS or FAIL reference pair.")
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


def _semantic_result_text(value: bool | None) -> str:
    if value is None:
        return "Not scored"
    return "Yes" if value else "No"


def _selected_row_index(index: int | tuple | list) -> int:
    row_index = index[0] if isinstance(index, (tuple, list)) else index
    try:
        return int(row_index)
    except (TypeError, ValueError) as error:
        raise gr.Error("Select a result row.") from error


def _select_workshop_tab(tab_id: str):
    return gr.Tabs(selected=tab_id)


def inspect_batch_row(evidence: dict | None, evt: gr.SelectData):
    if not evidence or not evidence.get("records"):
        raise gr.Error("Run this larger-set pass before selecting a result.")
    row_index = _selected_row_index(evt.index)
    records = evidence["records"]
    if row_index < 0 or row_index >= len(records):
        raise gr.Error("The selected row is outside the current result set.")

    record = records[row_index]
    reference = Image.open(record["reference"]).convert("RGB")
    observed = Image.open(record["live"]).convert("RGB")
    verdict_correct = record.get("expected") == record.get("verdict")
    detail = (
        f"### {record['pair_id']} · {record['analysis_mode']}\n"
        f"**Scene:** {record['scene']} · **Category:** {record['category']} · "
        f"**Error:** {record['error_type']}  \n"
        f"**Expected verdict:** {record['expected']} · **Predicted:** "
        f"{record['verdict']} · **Correct:** {'Yes' if verdict_correct else 'No'}  \n"
        f"**Expected action:** {record.get('expected_action') or '—'} · "
        f"**Action grounded:** {_semantic_result_text(record.get('action_correct'))} · "
        f"**Expected object:** {record.get('expected_item') or '—'} · "
        f"**Object grounded:** {_semantic_result_text(record.get('item_correct'))}  \n"
        f"**Confidence:** {record['confidence']} · **NIM:** "
        f"{record['latency_seconds']:.2f}s · **Preprocessing:** "
        f"{record['preprocessing_seconds']:.2f}s · **Total:** "
        f"{record['total_seconds']:.2f}s  \n"
        f"**Normalized issue used for scoring:** {record['issues']}"
    )
    model = model_from_label(record["model"])
    prompt_bundle = prompt_bundle_for(
        model,
        contour_assisted=record.get("analysis_mode") == "Contour-assisted",
    )
    if record.get("latency_seconds") == 0:
        prompt_bundle = (
            "NO NIM PROMPT WAS SENT: the expected and observed images were byte-identical, "
            "so the pipeline returned deterministic PASS.\n\n"
            "CONFIGURED PROMPT BUNDLE IF INFERENCE HAD BEEN REQUIRED\n\n"
            f"{prompt_bundle}"
        )
    return (
        reference,
        observed,
        detail,
        record.get("raw_response", ""),
        record.get("normalized_response", record.get("raw_response", "")),
        prompt_bundle,
    )


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

    records = add_semantic_scores(records)
    metrics = calculate_metrics(records)
    summary = (
        f"### {mode}: {metrics['correct']}/{metrics['pairs']} correct\n"
        f"**Accuracy:** {metrics['accuracy']:.0%} · **Precision:** {metrics['precision']:.0%} · "
        f"**Recall:** {metrics['recall']:.0%} · **F1:** {metrics['f1']:.0%}  \n"
        f"**Semantic action:** {metrics['action_accuracy']:.0%} "
        f"({metrics['action_total']} scored) · **Object/item:** "
        f"{metrics['item_accuracy']:.0%} ({metrics['item_total']} scored)"
    )
    rows = [
        [
            record["pair_id"],
            record["category"],
            record["expected"],
            record["verdict"],
            "Yes" if record["expected"] == record["verdict"] else "No",
            record.get("expected_action") or "—",
            _semantic_result_text(record.get("action_correct")),
            record.get("expected_item") or "—",
            _semantic_result_text(record.get("item_correct")),
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

    with gr.Blocks(title="Physical AI Visual Inspection") as demo:
        gr.Markdown(
            f"""<div class="hero">

# Physical AI Visual Inspection Workshop

Test how NVIDIA Cosmos can check a lab deck before an experiment starts by detecting
removed, added, moved, or changed equipment.

[Open the full workshop guide]({DOCS_URL})

</div>"""
        )

        with gr.Row(elem_classes=["status-row"]):
            with gr.Column(scale=1, min_width=0):
                status = gr.Markdown(_status_markdown(), elem_classes=["status-card"])
            with gr.Column(
                scale=0,
                min_width=190,
                elem_classes=["status-actions"],
            ):
                refresh_status = gr.Button(
                    "Refresh model status",
                    size="sm",
                    elem_classes=["status-refresh"],
                )
        refresh_status.click(_status_markdown, outputs=status)

        with gr.Tabs(
            selected="workshop-guide",
            elem_classes=["workshop-tabs"],
        ) as workshop_tabs:
            with gr.Tab("Workshop Guide", id="workshop-guide"):
                gr.Markdown(
                    f"[Open the full documented workshop guide ↗]({DOCS_URL})",
                    elem_classes=["guide-docs-link"],
                )
                phase_buttons = []
                with gr.Row(equal_height=True):
                    for title, description in PHASES:
                        with gr.Column(elem_classes=["guide-card"]):
                            phase_buttons.append(
                                gr.Button(
                                    title,
                                    elem_classes=["guide-card-button"],
                                )
                            )
                            gr.Markdown(description)

            with gr.Tab("1 · First Examples", id="first-examples"):
                gr.Markdown(
                    """
## Start with the curated examples

1. Load a pair and use its label as a dataset reference—not as a prediction exercise.
2. Run **Baseline** and read each model's original response.
3. Separate a correct verdict from a correct action, object, and location.
4. Notice misses, hallucinations, uncertainty, and differences between 2B and 8B.
5. Add contours on the same pair and ask what changed in both detection and meaning.
""",
                    elem_classes=["section-intro"],
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
                        label="Dataset reference label",
                        interactive=False,
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

                with gr.Row():
                    download_baseline = gr.DownloadButton("Download baseline JSON")
                    download_contour = gr.DownloadButton("Download contour JSON")
                download_baseline.click(export_result, inputs=baseline_state, outputs=download_baseline)
                download_contour.click(export_result, inputs=contour_state, outputs=download_contour)

            with gr.Tab("2 · Larger Set", id="larger-set"):
                gr.Markdown(
                    """
## Find the patterns—and the surprises

Choose a category and sample size. Run baseline first, then rerun the **same ordered
pairs** with contours. Select any row to inspect its images, raw response, semantics, and
prompt. Use precision and recall to discuss the real product trade-off: are false alarms
or missed changes more costly, and what amount of physical deviation should count?
""",
                    elem_classes=["section-intro"],
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
                gr.Markdown(
                    "Select any cell in either results table to inspect that pair below."
                )
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
                    headers=BATCH_COMPARISON_HEADERS,
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

                gr.Markdown("## Inspect a selected result")
                batch_selected_detail = gr.Markdown(
                    "Run a larger-set pass, then select any row from its output table."
                )
                with gr.Row(equal_height=True):
                    batch_selected_reference = gr.Image(
                        label="Expected image",
                        type="pil",
                        height=420,
                        interactive=False,
                    )
                    batch_selected_observed = gr.Image(
                        label="Observed image",
                        type="pil",
                        height=420,
                        interactive=False,
                    )
                with gr.Accordion("Model response and scoring normalization", open=True):
                    with gr.Row():
                        batch_selected_raw = gr.Code(
                            label="Original selected model response",
                            lines=14,
                            interactive=False,
                        )
                        batch_selected_normalized = gr.Code(
                            label="Normalized response used for scoring",
                            lines=14,
                            interactive=False,
                        )
                with gr.Accordion("Full configured prompt bundle for this result", open=False):
                    gr.Markdown(
                        "Includes the model/mode-specific full-frame prompt and the possible "
                        "local recovery sequence. Recovery messages are shown even when an "
                        "earlier response was accepted; image payloads use placeholders."
                    )
                    batch_selected_prompt = gr.Code(
                        label="Production prompt bundle",
                        lines=32,
                        interactive=False,
                    )

                selected_outputs = [
                    batch_selected_reference,
                    batch_selected_observed,
                    batch_selected_detail,
                    batch_selected_raw,
                    batch_selected_normalized,
                    batch_selected_prompt,
                ]
                batch_baseline_table.select(
                    inspect_batch_row,
                    inputs=batch_baseline_state,
                    outputs=selected_outputs,
                )
                batch_contour_table.select(
                    inspect_batch_row,
                    inputs=batch_contour_state,
                    outputs=selected_outputs,
                )

            with gr.Tab("3 · Explore", id="explore"):
                gr.Markdown(
                    """
## Customize the inspection stack with Codex/Claude

Use an agent inside the Brev workspace to understand the pipeline, explore one idea, and
measure whether it actually helps.
""",
                    elem_classes=["section-intro"],
                )
                gr.Markdown(
                    """
### Start in the Jupyter terminal

Open the terminal, then run either agent from the project:

```bash
cd /home/nvidia/physical-ai-visual-inspection
codex   # or: claude
```
""",
                    elem_classes=["agent-tutorial"],
                )
                if JUPYTER_URL:
                    gr.Button(
                        "Open Jupyter terminal ↗",
                        link=JUPYTER_URL,
                        link_target="_blank",
                        variant="primary",
                    )

                gr.Markdown(
                    """
### Main exploration prompt

Start with this, then let the conversation follow what interests you:

```text
Read the workshop context and use the visual-inspection workshop skill. Show me how this
project compares expected and observed deck images, where prompts and contours enter the
pipeline, and how verdict, action, object, hallucination, and latency are measured. Help
me characterize where 2B and 8B are useful or unreliable; whether contours improve
detection but change action or object quality; which object, action, nuisance, or edge
cases are missing; and what an ideal inspection case and acceptable physical tolerance
would be. Ask whether false positives or false negatives are more costly for the intended
workflow. Then propose one small exploration and explain what its result means for prompts,
conventional vision, data collection, or fine-tuning.
```

### Ideas to try next

- **Compare the models:** “Show me where 2B and 8B reason differently on the same pairs.”
- **Improve a prompt:** “Find one recurring reasoning error and suggest one small prompt change.”
- **Explore contours:** “Try a few contour settings on one difficult pair and explain the trade-offs.”
- **Inspect semantics:** “Print verdict, action, and object percentages, then show me the weakest examples.”
- **Choose the error trade-off:** “For this workflow, which is worse: a false alarm or a missed change?”
- **Define tolerance:** “What physical deviation should be acceptable, and what should trigger review?”
- **Find missing cases:** “Which object, action, or nuisance conditions are not represented here?”
- **Think about data:** “What labeled examples and held-out tests are needed before fine-tuning?”

Keep people, hands, PPE, annotations, and anything off the deck out of scope. Change one
thing at a time, use the same labeled pairs for comparisons, and ask before a large run
or model-service switch.
""",
                    elem_classes=["agent-tutorial"],
                )

                with gr.Accordion("Useful CLI starting points", open=False):
                    gr.Markdown(
                        """

```bash
./vision-inspect pairs --collection round1
./vision-inspect inspect --pair <pair-id> --models reason2-2b reason2-8b --mode both --raw
./vision-inspect batch --category Shift/Displace --count 10 --model reason2-8b --mode both
./vision-inspect sweep --pair <pair-id> --model reason2-8b --diff-methods color channel-max edges --thresholds 15 25 35 --min-areas 3000
```
""",
                    )

        phase_buttons[0].click(
            lambda: _select_workshop_tab("first-examples"),
            outputs=workshop_tabs,
            queue=False,
            scroll_to_output=True,
        )
        phase_buttons[1].click(
            lambda: _select_workshop_tab("larger-set"),
            outputs=workshop_tabs,
            queue=False,
            scroll_to_output=True,
        )
        phase_buttons[2].click(
            lambda: _select_workshop_tab("explore"),
            outputs=workshop_tabs,
            queue=False,
            scroll_to_output=True,
        )

    return demo


if __name__ == "__main__":
    build_demo().queue(default_concurrency_limit=2).launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        theme=NVIDIA_THEME,
        css=CSS,
    )
