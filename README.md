# Physical AI Visual Inspection Workshop

Evaluate how vision-language models reason about physical differences between expected
and observed workspace images.

**[Open the workshop guide](https://briandasantini.github.io/physical-ai-visual-inspection/)**
· [Launch instructions](https://briandasantini.github.io/physical-ai-visual-inspection/launch/)
· [CLI guide](https://briandasantini.github.io/physical-ai-visual-inspection/cli/)

The public repository contains code and documentation only. Approved workshop images
are supplied separately through a private, versioned NGC resource.

## What launches

- Cosmos Reason2 2B NIM on GPU 0
- Cosmos Reason2 8B NIM on GPU 1
- Optional Cosmos3 Nano image installed but stopped; it can replace 2B on GPU 0
- OpenCV contour preprocessing on CPU
- Visual inspection Gradio UI on port 7860
- Guided evaluation flow: first examples → larger set → contour-assisted rerun
- Searchable dataset explorer with pair loading
- Parallel 8B-versus-2B workshop comparison
- Persistent NIM model caches
- Health checks and workshop-safe status reporting

The workshop deliberately starts with a baseline (reference + live), then reruns the
same evidence with the validated contour-assisted path. This makes the effect on both
the verdict and reasoning visible.

## Run on a Brev VM

Use a VM with two supported GPUs and at least 250 GiB of disk.

```bash
cd <checkout>/physical-ai-visual-inspection
export NGC_API_KEY=<workshop-scoped-key>
export VISUAL_INSPECTION_DATA_RESOURCE=<org>/<team>/visual-inspection-workshop-data
./setup.sh
```

The first launch downloads the pinned private data resource, initializes both default
NIMs, and pulls the optional Nano container image without starting it.
Later runs on the same Brev instance reuse the data under `$HOME/workspace` and the
persistent Docker model caches. A brand-new instance downloads them once automatically;
attendees never upload files manually.

Open `http://<instance>:7860`, or configure a Brev Secure Link on port 7860.

The secure link opens the participant website directly. **Start Here** covers readiness
and safety; **Workshop Tutorial** provides timed, sequential exercises, expected evidence,
a progress checklist, controlled capture instructions, troubleshooting, and the closing decision.
Participants do not need terminal access for the normal hands-on flow.

The same workshop is also available as a CLI. See `CLI_GUIDE.md`, or start with:

```bash
./vision-inspect status
./vision-inspect pairs --collection round1
./vision-inspect inspect --pair <pair-id> --mode both --raw
```

## Agent-ready workshop

The repository includes a portable `visual-inspection-workshop` skill plus native entry
instructions for Codex, Claude Code, and GitHub Copilot. `setup.sh` guarantees that the
Codex and Claude Code CLIs are available, then links the skill into the Brev user's
agent directories. Existing working CLI installations are preserved. Agents learn to:

- follow first examples → larger set → contour rerun;
- use the supported CLI and preserve JSON evidence;
- compare verdict correctness and explanation grounding;
- protect customer data and the NGC credential;
- keep Nano off unless a facilitator explicitly selects it;
- preserve the safety boundary around model `PASS` results.

Reinstall or refresh the links manually with:

```bash
./scripts/install-agent-clis.sh
./scripts/install-agent-skill.sh
```

Participants can run an agent directly inside the Brev VM:

```bash
cd "$HOME/workspace/physical-ai-visual-inspection/physical-ai-visual-inspection"
codex
# or
claude
```

The first run asks the participant to authenticate with their own provider account.
Setup never stores or shares agent credentials. Cursor and VS Code are optional: a
participant can instead connect either editor to Brev over SSH and work in the same
repository. Because CLI authentication is stored in the Brev Linux user's home, do not
have multiple people sign personal accounts into one shared VM user; use one instance or
Linux account per operator when credential isolation is required.

For copy-paste setup commands and troubleshooting, see `REMOTE_EDITORS.md`.

The facilitator can activate Nano for an optional comparison. Nano and Reason2 2B share
GPU 0 and never run together; Reason2 8B remains on GPU 1:

```bash
export NGC_API_KEY=<workshop-scoped-key>
./scripts/select-model-set.sh nano
./scripts/select-model-set.sh reason2
```

Nano's first activation initializes its persistent model cache and can take several
minutes. Later switches on the same instance reuse that cache.

Useful commands:

```bash
./scripts/status.sh
docker compose logs -f visual-inspection-ui
docker compose logs -f nim-reason2-8b
docker compose down
```

## Create the one-click Launchable

Follow `BREV_CONFIG.md`. The intended Brev runtime is VM Mode with a setup script that authenticates to NGC and starts the isolated Compose stack. Deployers provide `NGC_API_KEY` as a required launch parameter.

Attach a public Git repository when creating the Launchable. Keep all private images in
a separate private NGC resource rather than adding them to the repository.

## Data handling

- Uploaded images are processed in memory by the UI.
- The app does not write uploads or inference results to persistent storage.
- Example data is mounted read-only.
- Only licensed public examples belong under `data/examples`.
- Approved datasets are versioned private NGC resources, not Git content.
- `VISUAL_INSPECTION_DATA_PROFILE=workshop` fetches the curated first examples and the approved
  larger evaluation subset.
- `VISUAL_INSPECTION_DATA_PROFILE=full` is reserved for private evaluation environments.
- The full Brev data layout and immutability rules are defined in `DATA_LAYOUT.md`.

To use an organized private dataset while developing in this repository:

```bash
export VISUAL_INSPECTION_DATA_DIR=/path/to/organized_data
docker compose up --build
```

## Local checks

The pure computer-vision and parsing checks do not require a GPU:

```bash
./scripts/smoke-test.sh
```

Full end-to-end validation requires the two NIM containers on supported NVIDIA GPUs.

On Brev, run one application-level check with an approved pair:

```bash
docker compose exec visual-inspection-ui python -m visual_inspection.smoke \
  /data/derived/workshop-pairs/pair_0001_cfg07_cam00_ill01_tm99_A_reference_ok.png \
  /data/derived/workshop-pairs/pair_0001_cfg07_cam00_ill01_tm99_B_test_error.png \
  --model reason2-8b
```

## Known limitation

This is a workshop system, not a production safety interlock. Small Shift/Displace errors remain the primary unresolved benchmark gap and must not be hidden behind the overall score.

## License

The workshop code and documentation are available under the Apache License 2.0. NVIDIA
NIM containers, Cosmos models, private datasets, and third-party dependencies remain
subject to their own terms.
