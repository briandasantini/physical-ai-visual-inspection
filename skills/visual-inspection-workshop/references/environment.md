# Environment reference

## Runtime

| Component | Assignment | Endpoint/state |
|---|---|---|
| Reason2 2B | GPU 0 | localhost `8001`, on by default |
| Reason2 8B | GPU 1 | localhost `8002`, on by default |
| Cosmos3 Nano | GPU 0 | localhost `8003`, installed but off |
| Participant app | CPU | port `7860` |

Reason2 2B and Nano are mutually exclusive. Reason2 8B remains running during either
GPU 0 selection.

## Repository and data

The normal Brev repository is:

```text
$HOME/workspace/physical-ai-visual-inspection/physical-ai-visual-inspection
```

The organized private data is mounted read-only at `/data` in the app container. It has:

- `derived/round1/index.json`: curated first examples.
- `derived/workshop-evaluation/index.json`: labeled evaluation pairs.

Code belongs in the public Git repository. The attendee bundle belongs in a private
GitHub Release; restricted source archives belong in approved SharePoint storage.
Experiment JSON belongs under the ignored `evidence/` directory.

## Agent entry points

Codex and Claude Code are installed or verified by `setup.sh`. Start either from the
repository so it discovers `AGENTS.md`, `CLAUDE.md`, and this skill:

```bash
codex
claude
```

The first run handles provider authentication. Never copy agent credentials into the
repository, SharePoint links, workshop evidence, or the shared NGC secret directory.
Cursor and VS Code may connect over SSH, but are not required inside the VM.

## Readiness and logs

```bash
./vision-inspect status
./scripts/status.sh
docker compose logs --tail 100 visual-inspection-ui
docker compose logs --tail 100 nim-reason2-8b
docker compose logs --tail 100 nim-reason2-2b
```

Do not print the secret. The approved persistent key path is:

```text
$HOME/.secrets/visual-inspection-ngc-key
```

## Optional Nano switch

Switch only after explicit user or facilitator approval:

```bash
export NGC_API_KEY="$(cat "$HOME/.secrets/visual-inspection-ngc-key")"
./scripts/select-model-set.sh nano
./vision-inspect status
```

Return to the default model set with:

```bash
export NGC_API_KEY="$(cat "$HOME/.secrets/visual-inspection-ngc-key")"
./scripts/select-model-set.sh reason2
```

Nano's first activation initializes its persistent cache and may take several minutes.

## Troubleshooting order

1. Run `./vision-inspect status`.
2. Confirm the app container is healthy and indexes the configured collections.
3. Check only the failing service's last 100 log lines.
4. Confirm the selected GPU 0 model matches the requested model.
5. Retry one labeled pair before a batch.
6. Preserve the failure as evidence instead of changing labels or prompts mid-comparison.
