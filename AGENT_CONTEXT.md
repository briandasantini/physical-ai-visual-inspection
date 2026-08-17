# Physical AI visual inspection agent context

## Purpose

This repository is a reusable deployment product for a Physical AI visual inspection
workshop. The system compares an expected workspace image with an observed image,
generates an OpenCV contour-assisted view,
and asks NVIDIA Cosmos Reason2 NIM for a structured PASS/FAIL assessment.

This is a workshop and evaluation system, not a production safety interlock.

## Runtime architecture

- Cosmos Reason2 2B NIM runs on GPU 0 and localhost port 8001.
- Cosmos Reason2 8B NIM runs on GPU 1 and localhost port 8002.
- Optional Cosmos3 Nano uses GPU 0 and localhost port 8003. Its image is installed but
  the service is stopped by default; it replaces Reason2 2B when activated.
- The Gradio participant website runs on port 7860.
- Docker Compose isolates all three services.
- NIM caches use persistent Docker volumes.
- Approved workshop data is downloaded from a private GitHub Release, verified, cached,
  and mounted read-only from a persistent Brev workspace directory. SharePoint remains
  the restricted system of record and fallback for the full archive; NGC supplies the
  licensed NIM images.

The intended machine is a Brev VM with two H100-class GPUs. The tested NIM tag is
`1.7.0`.

`setup.sh` also guarantees that Codex and Claude Code are callable inside the VM. It
does not authenticate either agent. Each participant signs in on first use; Cursor and VS
Code remain optional remote-SSH clients rather than launchable dependencies.

## Repository map

- `setup.sh`: idempotent Brev bootstrap.
- `compose.yaml`: dual-NIM and participant-site stack.
- `app/src/visual_inspection/ui.py`: first examples, larger-set, contour rerun, and exploration pages.
- `app/src/visual_inspection/cli.py`: equivalent status, pair, Round 1, inspection, and batch terminal commands.
- `vision-inspect`: host-side wrapper for running the CLI inside the application container.
- `AGENTS.md`: repository-wide operating and code-change instructions for agents.
- `skills/visual-inspection-workshop/`: portable workshop guidance and evaluation skill.
- `scripts/install-agent-clis.sh`: verifies or installs Codex and Claude Code with their official native installers.
- `scripts/install-agent-skill.sh`: links the skill into Codex, generic agent, and Claude directories.
- `REMOTE_EDITORS.md`: optional Cursor and VS Code connection instructions for participants.
- `app/src/visual_inspection/tutorial.py`: workshop phases and progress gates.
- `app/src/visual_inspection/vision.py`: contour preprocessing.
- `app/src/visual_inspection/nim_client.py`: health checks and structured NIM inference.
- `app/src/visual_inspection/datasets.py`: workshop and evaluation dataset indexing.
- `data/profiles.json`: approved workshop/full bundle contents and versions.
- `scripts/fetch-data.py`: downloads, validates, caches, and atomically activates data.
- `scripts/prepare-data-bundle.py`: builds a deterministic distribution bundle.
- `scripts/organize-private-deliveries.py`: organizes untracked source deliveries.
- `BREV_CONFIG.md`: values for the Brev Launchable builder.
- `DATA_LAYOUT.md`: private data lifecycle and directory contract.

## Data contract

Do not add private images, videos, archives, sharing links, credentials, or inference
exports to Git. Git contains code and generic profile manifests only. Private data is
distributed through verified bundles:

- `workshop`: private GitHub Release containing curated first examples and an approved
  evaluation subset.
- `full`: restricted SharePoint bundle containing the extracted evaluation corpus plus
  every preserved original delivery.

On first launch, the selected resource is downloaded under
`$HOME/workspace/visual-inspection-data/versions/<profile>/<version>`. The `current` symlink is
switched only after inventory validation. Later starts reuse the local cache.

## Validated behavior

- The participant website builds with Gradio 6.20.0.
- Unit tests cover image preprocessing, NIM response parsing, dataset indexing, data
  downloads, CLI workflows, and tutorial behavior.
- The data bootstrap has been exercised with a mock registry and skips a second download
  after validating the cached version.
- The application path has run against both 2B and 8B NIMs on a two-H100 Brev instance.
Model accuracy is not perfect. Verdict correctness and explanation grounding must be
evaluated separately. Small Shift/Displace changes are a known challenge category.

## Local validation

```bash
PYTHONPATH=app/src python3 -m unittest discover -s app/tests -p 'test_*.py'
PYTHONPATH=app/src python3 -c 'from visual_inspection.ui import build_demo; build_demo()'
```

Full end-to-end validation requires two supported NVIDIA GPUs, NGC access to both NIMs,
and read access to the private workshop resource.

## Remaining deployment work

1. Publish the pinned `workshop-2026.08.15` asset in the private data repository.
2. Create a fine-grained token limited to read-only repository contents.
3. Configure the final Brev Launchable and Secure Link on port 7860.
4. Test a newly created instance from the final Launchable URL.
