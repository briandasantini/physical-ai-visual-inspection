# Physical AI Visual Inspection Workshop

Test how NVIDIA Cosmos can check a lab automation deck before an experiment starts by
comparing its expected and observed state and detecting removed, added, moved, replaced,
or reconfigured equipment.

## Objective

The objective is to discover where vision-language models are useful for deck inspection,
where they miss meaningful changes, and where they produce a correct verdict for the wrong
reason. We will also test whether pixel-level contour cues focus the models or distort their
understanding of the action and object.

This is an exploration rather than a production certification or model leaderboard. Dataset
labels are reference annotations, and people, hands, PPE, annotations, and anything outside
the deck are not valid inspection evidence.

## NVIDIA Cosmos vision-language models

NVIDIA Cosmos is a family of open models for physical AI. This workshop explores two
series: Cosmos Reason2 and Cosmos3.

### Cosmos Reason2

- **Sizes:** [2B](https://huggingface.co/nvidia/Cosmos-Reason2-2B),
  [8B](https://huggingface.co/nvidia/Cosmos-Reason2-8B), and
  [32B](https://huggingface.co/nvidia/Cosmos-Reason2-32B)
- **Base architecture:** Qwen3-VL 2B, 8B, and 32B respectively
- **Type:** post-trained vision-language model
- **Capabilities:** spatio-temporal reasoning, object detection with 2D/3D localization,
  long-context video up to 256K tokens, and chain-of-thought reasoning
- **Precision:** BF16 only; minimum 32 GB GPU memory
- **Learn more:** [GitHub](https://github.com/nvidia-cosmos/cosmos-reason2) ·
  [intro video](https://www.youtube.com/watch?v=kcrDwWgRoTo&t=193s)

### Cosmos3

- **Sizes:** [Nano](https://huggingface.co/nvidia/Cosmos3-Nano), with an 8B reasoner and
  8B generator, and [Super](https://huggingface.co/nvidia/Cosmos3-Super), with a 32B
  reasoner and 32B generator
- **Architecture:** Mixture-of-Transformers with reasoner and generator towers sharing a
  common representation
- **Reasoner tower:** scene understanding, reasoning, and next-token prediction
- **Generator tower:** video, audio, and action-sequence generation; not tested here
- **Learn more:** [Cosmos3 overview](https://huggingface.co/blog/nvidia/cosmos-3-for-physical-ai) ·
  [reasoner cookbook](https://github.com/NVIDIA/cosmos/tree/main/cookbooks/cosmos3/reasoner) ·
  [Nano Reasoner NIM](https://catalog.ngc.nvidia.com/orgs/nim/nvidia/containers/cosmos3-reasoner)

For simplicity, the hands-on exercises use the two smallest Reason2 configurations, 2B
and 8B. Cosmos3 Nano Reasoner is available as an optional comparison. Reason2 32B and
Cosmos3 Super are introduced here but are not started in the workshop environment.

## What we are exploring

The workshop asks where the models reason well, where they miss meaningful changes, and
where they hallucinate unsupported ones. It also asks whether pixel-level contour cues
improve detection or alter action and object quality, which false-positive/false-negative
trade-off the intended workflow needs, what physical tolerance is acceptable, which cases
are missing, and what data would be necessary before fine-tuning.

## What we will do

### 1 · Test the first five examples

Start with five curated image pairs covering a matching setup and several kinds of deck
change. Compare Cosmos Reason2 2B and 8B, read their original responses, and separate the
PASS/FAIL verdict from the reported action, object, location, and hallucinations. Then add
contour cues to the same examples and see what improves or regresses.

### 2 · Test a larger set

Move beyond the five examples to a selected category and a larger labeled sample. Compare
accuracy, precision, recall, action and object quality, latency, and individual failures.
Use the results to discuss whether false alarms or missed changes matter more and whether
the dataset is missing important objects, actions, tolerances, or nuisance conditions.

### 3 · Explore with Codex or Claude

Use the Jupyter terminal to investigate one open question about prompts, contours, model
behavior, acceptable physical tolerances, missing cases, or data needed before fine-tuning.

[Continue to the Workshop Map](workshop/index.md){ .launch-button }
