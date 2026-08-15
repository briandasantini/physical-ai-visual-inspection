# Architecture

The Launchable uses a two-GPU Brev VM and an isolated Docker Compose stack.

```text
Participant browser
        |
        | Brev Secure Link :7860
        v
Gradio visual-inspection UI
        |
        +--> OpenCV contour preprocessing on CPU
        |
        +--> Cosmos Reason2 2B NIM  :8001  GPU 0
        |
        +--> Cosmos Reason2 8B NIM  :8002  GPU 1
        |
        +--> Cosmos3 Nano NIM       :8003  GPU 0  optional/off
        |
        +--> approved dataset mounted read-only
```

NIM ports bind to localhost and are not public. Only the Gradio website is exposed
through a Brev Secure Link.

## Runtime behavior

- `setup.sh` validates two NVIDIA GPUs.
- The setup downloads the pinned SharePoint bundle and verifies both outer and per-file
  SHA-256 checksums.
- Docker authenticates to NGC without printing the key.
- Reason2 2B and 8B start by default.
- The Nano image is pulled but remains stopped.
- Model caches and downloaded data persist across stop/start cycles of the same VM.

The system is an evaluation environment, not a production safety interlock.
