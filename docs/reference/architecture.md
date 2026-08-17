# Architecture

The Launchable uses a two-GPU Brev VM, an isolated Docker Compose stack, and Brev's
managed JupyterLab service.

```text
Participant browser
        |
        +--> Brev Secure Link :7860
        |       +--> Gradio visual-inspection UI
        |               +--> approved dataset mounted read-only
        |               +--> OpenCV contour preprocessing on CPU
        |               +--> Cosmos Reason2 2B NIM :8001 GPU 0
        |               +--> Cosmos Reason2 8B NIM :8002 GPU 1
        |               +--> Cosmos3 Nano NIM      :8003 GPU 0 optional/off
        |
        +--> Brev JupyterLab link
                +--> Jupyter terminal on the VM host
                +--> Codex or Claude
                +--> repository and ./vision-inspect CLI
```

NIM ports bind to localhost and are not exposed publicly. The Gradio app derives the
Jupyter URL from `BREV_ENV_ID` or an explicit `VISUAL_INSPECTION_JUPYTER_URL`.

## Runtime behavior

- `setup.sh` validates two NVIDIA GPUs.
- The setup downloads the pinned private GitHub Release asset and verifies outer and
  per-file SHA-256 checksums.
- Docker authenticates to NGC without printing the key.
- Reason2 2B and 8B start by default.
- The Nano image is pulled but remains stopped.
- Model caches and downloaded data persist across stop/start cycles of the same VM.
- Codex and Claude run in the Jupyter terminal and authenticate with the operator's own
  provider account.
