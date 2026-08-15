# Troubleshooting

## The secure link is unavailable

Wait for the setup script to finish, then check:

```bash
./scripts/status.sh
docker compose logs --tail 100 visual-inspection-ui
```

The Brev Secure Link must target port `7860`.

## A model stays yellow

NIM initialization can take several minutes on first launch. Check the service without
exposing environment variables:

```bash
docker compose ps
docker compose logs --tail 100 nim-reason2-8b
```

Confirm the VM has two supported GPUs and that the NGC key can access the required NIMs.

## The dataset does not load

Run:

```bash
readlink "$HOME/workspace/visual-inspection-data/current"
./vision-inspect pairs --collection round1
```

Do not manually edit downloaded files. Resource validation intentionally fails when a
file path, size, or checksum differs from the pinned manifest.

## Nano is unavailable

Nano is intentionally off. A facilitator can activate it with:

```bash
./scripts/select-model-set.sh nano
```

This stops Reason2 2B because both use GPU 0. Reason2 8B remains available on GPU 1.

## Cursor or VS Code cannot connect

From the laptop:

```bash
brev login
brev ls
brev refresh
```

Then retry `brev open`. Closing the editor does not stop the Brev instance.

## An agent skips the experiment order

Confirm the agent started in the repository root and ask it to read `AGENTS.md`. Record
the expected label before allowing inference.
