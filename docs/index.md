# Physical AI Visual Inspection Workshop

Test how NVIDIA Cosmos can check a lab automation deck before an experiment starts by
comparing its expected and observed state and detecting removed, added, moved, replaced,
or reconfigured equipment.

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

The hands-on exercises use Cosmos Reason2 2B and 8B. Cosmos3 Nano Reasoner is available
as an optional comparison. Reason2 32B and Cosmos3 Super are introduced here but are not
started in the workshop environment.

## Objective

The objective is to discover where the models reason well, where they miss meaningful
deck changes, and where they hallucinate unsupported ones. We will test whether pixel-level
contour cues improve detection or alter action and object quality, which false-positive or
false-negative trade-off the intended workflow needs, what physical tolerance is
acceptable, which cases are missing, and what data would be necessary before fine-tuning.

## Workshop Map

The workshop moves from concrete model behavior to application questions and a data plan.
Each phase should create a conversation, not just an exported score.

| Phase | Explore together | Useful evidence |
|---|---|---|
| [1 · First examples](workshop/first-examples.md) | Where do 2B and 8B succeed, miss, disagree, or hallucinate? | Images plus original responses and semantic observations |
| [2 · Larger set](workshop/larger-set.md) | Which patterns generalize, and which new failure types appear? | Verdict/action/object metrics plus selected rows |
| [Contour cues](workshop/contours.md) | Do cues help detection, hurt semantics, or create false alarms? | Matched baseline/contour cases |
| [3 · Agent experiment](workshop/explore.md) | What should we investigate next about prompts, cues, tolerances, gaps, or data? | One focused exploration and its implication |

### Keep these questions open

- Is the model right for the right physical reason?
- Does a contour change only the verdict, or also action and object quality?
- Which error is worse here: a false alarm or a missed change?
- What physical deviation should be accepted, rejected, or sent to human review?
- Which object, action, nuisance condition, or edge case have we not tested?
- What would an ideal case and a difficult but realistic counterexample look like?
- What data and held-out test would justify fine-tuning?

### Read evidence on separate axes

1. **Verdict:** Does the result match the dataset reference label?
2. **Semantics:** Does it name the real action, object, and location?
3. **Hallucination:** Does it invent unsupported physical evidence?
4. **Cue effect:** Did contours help, hurt, or merely change confidence?
5. **Error trade-off:** What do false alarms and missed changes mean operationally?
6. **Coverage:** Is the case set missing something important?
7. **Latency:** Is the observed benefit worth the preprocessing and total cost?

A correct verdict with an invented explanation is not a clean success, and a good
aggregate score can still hide the error type that matters most.
