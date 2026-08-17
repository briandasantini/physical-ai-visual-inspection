# Physical AI Visual Inspection Workshop

Test how NVIDIA Cosmos can check a lab automation deck before an experiment starts by
comparing expected and observed images and detecting removed, added, moved, replaced,
or reconfigured equipment.

**[Open the workshop guide](https://briandasantini.github.io/physical-ai-visual-inspection/?v=20260817-start-here-v3)**

This public repository contains the participant website, CLI, Brev setup, and reusable
Codex/Claude workshop instructions. Workshop images are supplied separately and are
never committed here.

## What we will explore

The hands-on exercises compare Cosmos Reason2 2B and 8B, with Cosmos3 Nano available as
an optional comparison. We examine where the models succeed, miss, disagree, or
hallucinate, and whether OpenCV contour cues improve detection or change action and
object quality.

## Workshop flow

1. **First examples** — compare both models on five curated image pairs and inspect
   their original responses.
2. **Larger set** — test whether the same patterns hold across a broader sample and
   inspect verdict, action, object, and latency evidence.
3. **Explore** — use Codex or Claude to investigate prompts, contour settings,
   tolerances, missing cases, or data needed before fine-tuning.

## Start here

- [Workshop guide](https://briandasantini.github.io/physical-ai-visual-inspection/?v=20260817-start-here-v3)
- [Launch the environment](https://briandasantini.github.io/physical-ai-visual-inspection/launch/)
- [Use the CLI](https://briandasantini.github.io/physical-ai-visual-inspection/cli/)
- [Work with Codex or Claude](https://briandasantini.github.io/physical-ai-visual-inspection/agents/)

## Technical references

- [BREV_CONFIG.md](BREV_CONFIG.md) — create and configure the Brev Launchable
- [CLI_GUIDE.md](CLI_GUIDE.md) — detailed terminal workflows
- [REMOTE_EDITORS.md](REMOTE_EDITORS.md) — connect Cursor or VS Code
- [DATA_LAYOUT.md](DATA_LAYOUT.md) — private-data layout and integrity rules
- [`skills/visual-inspection-workshop/`](skills/visual-inspection-workshop/) — reusable
  agent instructions

## License

The workshop code and documentation are available under the Apache License 2.0. NVIDIA
NIM containers, Cosmos models, private datasets, and third-party dependencies remain
subject to their own terms.
