# Visual inspection agent instructions

Read `AGENT_CONTEXT.md`, `WORKSHOP_FLOW.md`, and `CLI_GUIDE.md` before operating or
modifying this repository. For workshop guidance, also use
`skills/visual-inspection-workshop/SKILL.md`.

## Operating rules

- Use `./vision-inspect` instead of direct NIM API calls for workshop exercises.
- Record the expected label before inference.
- Run baseline before contour assistance and compare the same pair/sample.
- Judge verdict correctness and explanation grounding separately.
- Keep generated JSON under `evidence/`.
- Treat `FAIL` as the positive class for precision, recall, and F1.
- Never interpret a model `PASS` as authorization to release a robotic run.
- Never expose `$HOME/.secrets/visual-inspection-ngc-key` or put credentials in commands,
  outputs, logs, commits, or evidence.
- Never print, persist, or commit `VISUAL_INSPECTION_DATA_URL`; treat the SharePoint
  download link as a secret.
- Never add private images, archives, or inference evidence to Git.
- Never run Nano and Reason2 2B together; use `scripts/select-model-set.sh`.
- Ask before switching models, stopping Brev, or running a large batch.

## Code changes

- Keep the CLI and browser app on shared dataset, vision, NIM, parsing, and metric code.
- Preserve the configured curated-pair order and evaluation manifest.
- Run `PYTHONPATH=app/src python3 -m unittest discover -s app/tests -p 'test_*.py'`.
- Validate UI construction with
  `PYTHONPATH=app/src python3 -c 'from visual_inspection.ui import build_demo; build_demo()'`.
- Do not fix unrelated research-repository issues from this clean launchable.
