# Launch the Environment

The workshop is packaged as an NVIDIA Brev Launchable. A new deployment creates the VM,
clones the public code, downloads the approved private dataset, starts the NVIDIA NIMs,
and exposes the participant website through a Brev Secure Link.

## Participant launch

1. Open the workshop Launchable URL supplied by the facilitator.
2. Sign in to Brev.
3. Choose the recommended two-GPU configuration.
4. Enter the workshop-scoped `NGC_API_KEY` when prompted.
5. Select **Deploy**.
6. Wait for setup to finish and open **Open Visual Inspection**.

!!! info "First launch"
    A new instance must download model containers and the pinned workshop dataset.
    Restarting the same instance reuses the persistent data and model caches.

## Readiness check

The website displays model status at the top. Begin when:

- **Cosmos Reason2 8B** is green;
- the curated and larger-set examples load;
- optional Cosmos3 Nano is off unless the facilitator selected it.

Terminal users can run:

```bash
./vision-inspect status
```

## Connect an editor

Cursor and VS Code are optional. Install the Brev CLI and your editor on your laptop,
then run one of these commands:

```bash
brev open <instance-name> code \
  --dir /home/nvidia/workspace/physical-ai-visual-inspection/physical-ai-visual-inspection

brev open <instance-name> cursor \
  --dir /home/nvidia/workspace/physical-ai-visual-inspection/physical-ai-visual-inspection
```

Closing an editor does not stop the paid instance. Stop the instance in Brev when the
workshop is complete.

## Credentials

- The NGC key must be workshop-scoped and is entered as a Brev setup value.
- Codex and Claude authenticate separately with each participant's provider account.
- Do not sign multiple personal agent accounts into one shared Linux user.
- Never paste credentials into prompts, evidence files, Git, or screenshots.
