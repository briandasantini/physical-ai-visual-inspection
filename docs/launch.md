# Launch the Environment

The workshop is packaged as an NVIDIA Brev Launchable. A new deployment creates the VM,
clones the public code, downloads the approved private dataset, starts the NVIDIA NIMs,
and exposes the participant website through a Brev Secure Link.

## Participant launch

1. Open the Launchable URL provided for the workshop.
2. Sign in to Brev.
3. Choose the recommended two-GPU configuration.
4. Enter the workshop-scoped `NGC_API_KEY` when prompted.
5. Enter the fine-grained private-data GitHub token provided for the workshop.
6. Select **Deploy**.
7. Wait for setup to finish and open **Open Visual Inspection**.
8. Use an **Open Jupyter terminal** button when the agent-guided experiment begins.

!!! info "First launch"
    A new instance must download model containers and the pinned workshop dataset.
    Restarting the same instance reuses the persistent data and model caches.

## Readiness check

The website displays model status at the top. Begin when:

- **Cosmos Reason2 8B** is green;
- the curated and larger-set examples load;
- JupyterLab opens in a new tab and `./vision-inspect status` runs from its Terminal.

Terminal users can run:

```bash
./vision-inspect status
```

## Connect an editor

Cursor and VS Code are optional. Install the Brev CLI and your editor on your laptop,
select the workshop organization, then open the instance:

```bash
brev login
brev org ls
brev org set <workshop-org>
brev ls
brev refresh
```

Use the `<workshop-org>` name provided for the workshop. Then run one of these commands:

```bash
brev open <instance-name> code \
  --dir /home/nvidia/workspace/physical-ai-visual-inspection/physical-ai-visual-inspection

brev open <instance-name> cursor \
  --dir /home/nvidia/workspace/physical-ai-visual-inspection/physical-ai-visual-inspection
```

Closing an editor does not stop the paid instance. Stop the instance in Brev when the
workshop is complete.

## Credentials

- The NGC key is used only for the licensed NIMs.
- The GitHub token must have Contents: Read-only access to the private data repository.
- Treat both values as secrets and never use a broad personal token.
- Codex and Claude authenticate separately with your provider account.
- Use one authenticated agent account per shared environment.
- Never paste credentials into prompts, evidence files, Git, or screenshots.
