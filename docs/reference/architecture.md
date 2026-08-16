# Architecture

The Launchable uses a two-GPU Brev VM and an isolated Docker Compose stack.

```text
Participant browser
        |
        | Brev Secure Link :7860
        v
Nginx workshop gateway
        |
        +--> Gradio visual-inspection UI
        |       +--> OpenCV contour preprocessing on CPU
        |       +--> approved dataset mounted read-only
        |
        +--> ttyd agent terminal
        |       +--> Codex or Claude
        |       +--> repository mounted read/write
        |       +--> approved dataset mounted read-only
        |
        +--> Cosmos Reason2 2B NIM  :8001  GPU 0
        +--> Cosmos Reason2 8B NIM  :8002  GPU 1
        +--> Cosmos3 Nano NIM       :8003  GPU 0  optional/off
```

NIM ports bind to localhost and are not public. The gateway exposes the UI and terminal
through one authenticated Brev Secure Link. The terminal has no Docker socket and no NGC
or private-data launch variables.

## Runtime behavior

- `setup.sh` validates two NVIDIA GPUs.
- The setup downloads the pinned private GitHub Release asset and verifies outer and per-file
  SHA-256 checksums.
- Docker authenticates to NGC without printing the key.
- Reason2 2B and 8B start by default.
- The Nano image is pulled but remains stopped.
- Model caches and downloaded data persist across stop/start cycles of the same VM.
- Agent authentication persists only in the environment's dedicated terminal-home volume.
