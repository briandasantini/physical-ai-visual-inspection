# Physical AI Visual Inspection Workshop

Explore how vision-language models reason about physical differences between expected
and observed workspace images, where they miss or hallucinate, and what the intended
inspection workflow should require.

**[Open the workshop guide](https://briandasantini.github.io/physical-ai-visual-inspection/)**
· [Launch instructions](https://briandasantini.github.io/physical-ai-visual-inspection/launch/)
· [CLI guide](https://briandasantini.github.io/physical-ai-visual-inspection/cli/)

The public repository contains code and documentation only. Approved workshop images
are supplied separately through a private GitHub Release. Restricted source archives
remain in approved SharePoint storage, and NGC supplies only the licensed NIM images.

## What launches

- Cosmos Reason2 2B NIM on GPU 0
- Cosmos Reason2 8B NIM on GPU 1
- Optional Cosmos3 Nano image installed but stopped; it can replace 2B on GPU 0
- OpenCV contour preprocessing on CPU
- Visual inspection Gradio UI on port 7860, with links to Brev's JupyterLab terminal
- Guided flow: first examples → larger-set patterns → open agent-led investigation
- Parallel 8B-versus-2B workshop comparison
- Verdict, action, item, contour, NIM latency, preprocessing latency, and total latency evidence
- Persistent NIM model caches
- Codex and Claude installed in the Brev host environment
- Health checks and workshop-safe status reporting

The workshop uses baseline and contour-assisted views of the same evidence to separate
model behavior from cue effects. Participants examine verdict, action, object, location,
hallucinations, and latency; discuss false-positive versus false-negative cost and
acceptable physical tolerance; identify missing cases; and decide what data or controls
would be needed next. It is not a PASS/FAIL certification or a model leaderboard.

## Run on a Brev VM

Use a VM with two supported GPUs and at least 250 GiB of disk.

```bash
cd <checkout>/physical-ai-visual-inspection
export NGC_API_KEY=<workshop-scoped-key>
export VISUAL_INSPECTION_DATA_GITHUB_TOKEN=<fine-grained-read-only-token>
export VISUAL_INSPECTION_DATA_SHA256=<pinned-bundle-sha256>
./setup.sh
```

The first launch downloads the pinned private GitHub Release bundle, initializes both default
NIMs, and pulls the optional Nano container image without starting it.
Later runs on the same Brev instance reuse the data under `$HOME/workspace` and the
persistent Docker model caches. A brand-new instance downloads them once automatically;
attendees never upload files manually.

Open `http://<instance>:7860`, or configure a Brev Secure Link on port 7860.

The secure link opens the participant website directly. The first two phases use guided
web controls; the third links to the Brev-hosted JupyterLab terminal for Codex/Claude.

The same workshop is also available as a CLI. See `CLI_GUIDE.md`, or start with:

```bash
./vision-inspect status
./vision-inspect pairs --collection round1
./vision-inspect inspect --pair <pair-id> --mode both --raw
```

## Agent-ready workshop

The repository includes a portable `visual-inspection-workshop` skill plus native entry
instructions for Codex, Claude Code, and GitHub Copilot. Setup installs Codex and Claude
on the Brev host and links the workshop skill into each agent directory. Existing working
CLI installations are preserved. Agents learn to:

- support collaborative discovery rather than ask participants to guess labels;
- find model strengths, misses, hallucinations, and semantic errors;
- use the supported CLI and preserve JSON evidence;
- compare verdict, action, object, location, cues, and latency on matched cases;
- connect precision and recall to false-alarm and missed-change cost;
- ask about physical tolerances, ideal cases, missing coverage, and fine-tuning data;
- run controlled cue-method, threshold, and region-area sweeps when useful;
- protect customer data and the NGC credential;
- keep Nano off unless it is explicitly selected.

Reinstall or refresh the links manually with:

```bash
./scripts/install-agent-clis.sh
./scripts/install-agent-skill.sh
```

Participants can use the Jupyter button in the website, open **Terminal** from the
JupyterLab Launcher, and start an agent from the repository:

```bash
cd /home/nvidia/physical-ai-visual-inspection
./vision-inspect status
codex
# or
claude
```

The first run asks the participant to authenticate with their own provider account.
Setup never stores or shares agent credentials. Cursor and VS Code are optional: a
participant can instead connect either editor to Brev over SSH and work in the same
repository. Because authentication persists in the environment's terminal home, use one
authenticated agent account per shared environment and remove the environment when the workshop is complete.

For copy-paste setup commands and troubleshooting, see `REMOTE_EDITORS.md`.

Nano can be activated for an optional comparison. Nano and Reason2 2B share
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

Follow `BREV_CONFIG.md`. The intended Brev runtime is VM Mode with a setup script that
authenticates to NGC, downloads the private workshop release, and starts the isolated
Compose stack. Deployers provide an approved `NGC_API_KEY` for the NIMs and a fine-grained
read-only GitHub token for the private data repository.

Attach the public code repository when creating the Launchable. Keep workshop images in
the separate private data repository and restricted source archives in approved
SharePoint storage.

## Data handling

- Uploaded images are processed in memory by the UI.
- The app does not write uploads or inference results to persistent storage.
- Example data is mounted read-only.
- Only licensed public examples belong under `data/examples`.
- Approved workshop datasets are private GitHub Release assets, not Git history.
- Restricted source archives and the full bundle remain in approved SharePoint storage.
- `VISUAL_INSPECTION_DATA_PROFILE=workshop` fetches the curated first examples and the approved
  larger evaluation subset.
- `VISUAL_INSPECTION_DATA_PROFILE=full` includes the extracted evaluation corpus and
  preserved original deliveries for restricted environments.
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

## Known evaluation gap

Small Shift/Displace errors remain the primary unresolved benchmark gap and must not be
hidden behind the overall score. Compare verdict accuracy with action/item grounding and
the raw response.

## License

The workshop code and documentation are available under the Apache License 2.0. NVIDIA
NIM containers, Cosmos models, private datasets, and third-party dependencies remain
subject to their own terms.
