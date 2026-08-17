# Brev Launchable configuration

Use these values in the Brev Launchable builder.

## Details

- **Name:** `Physical AI Visual Inspection Workshop`
- **Description:** `Compares expected and observed workspace images with Cosmos Reason2, optional Cosmos3 Nano, labeled datasets, and OpenCV contour assistance.`
- **Workshop guide:** `https://briandasantini.github.io/physical-ai-visual-inspection/`

## Hardware

- **Default:** 2× H100 80 GB
- **Disk:** 250 GiB minimum
- **Reason:** GPU 0 serves Reason2 2B or optional Nano; GPU 1 continuously serves Reason2 8B.

## Software

- **Runtime mode:** VM Mode
- **Setup script:** Use the bootstrap script below. It installs or verifies Codex and Claude Code, links the workshop skill, logs Docker into NGC without printing the key, then starts `compose.yaml`.
- **Jupyter:** On. Exercise 3 links directly to its terminal for Codex/Claude.

VM Mode is required because the NIM containers come from a registry that needs an NGC
credential. The Brev Launchable creation guide recommends VM Mode when containers need
private-registry or API-key authentication. Expect a new deployment to take at least
10–20 minutes while the VM, data, and NIM caches initialize; show this expectation in
the participant instructions.

```bash
#!/usr/bin/env bash
set -euo pipefail

SETUP_PATH="$(find "$HOME" -type f -path '*/physical-ai-visual-inspection*/setup.sh' -print -quit)"
if [[ -z "$SETUP_PATH" ]]; then
  echo "Could not find the physical-ai-visual-inspection setup.sh under $HOME." >&2
  exit 1
fi

bash "$SETUP_PATH"
```

VM Mode is the workshop-safe default because the setup script performs the required NGC registry login before Docker pulls the private NIM images. The application still runs as the reproducible Compose stack.

## Source

- Use `https://github.com/briandasantini/physical-ai-visual-inspection` as the public
  Launchable source.
- Keep the workshop bundle as a Release asset in the separate private data repository
  and restricted source archives in approved SharePoint storage. Never add private data
  to the public repository or Git history.

## Network

- **Secure Link name:** `Open Visual Inspection`
- **Port:** `7860`
- **Call to action:** On
- Do not expose NIM ports publicly. Ports 8001, 8002, and 8003 bind to localhost only.

Use a secured HTTP link rather than a public port. The Brev guide identifies secured
tunnels as the intended access path for Gradio and similar participant applications.

## Launch parameters

| Name | Type | Required | Default | Purpose |
|---|---|---:|---|---|
| `NGC_API_KEY` | Text | Yes | None | Pulls and initializes the NIMs. Use an approved key. |
| `VISUAL_INSPECTION_DATA_GITHUB_TOKEN` | Text | Yes | None | Fine-grained token with Contents: Read-only access to the private data repository. |
| `NIM_TAG` | Choice | No | `1.7.0` | Pins the tested VLM NIM release. |
| `VISUAL_INSPECTION_INSTALL_NANO` | Choice | No | `true` | Pulls Nano but leaves it stopped. |
| `VISUAL_INSPECTION_INSTALL_AGENT_CLIS` | Choice | No | `true` | Guarantees Codex and Claude Code are available in the VM. |
| `VISUAL_INSPECTION_INSTALL_AGENT_SKILL` | Choice | No | `true` | Links the workshop skill for supported agents. |
| `VISUAL_INSPECTION_CLAUDE_CHANNEL` | Choice | No | `stable` | Uses Anthropic's stable native release channel. |
| `VISUAL_INSPECTION_DATA_PROFILE` | Choice | No | `workshop` | Selects the curated or restricted full bundle. |
| `VISUAL_INSPECTION_DATA_SOURCE` | Choice | No | `github` | Uses the private GitHub Release for attendees. Use `sharepoint` only in a restricted deployment. |
| `VISUAL_INSPECTION_DATA_GITHUB_REPOSITORY` | Text | No | `briandasantini/physical-ai-visual-inspection-data` | Private repository containing the release asset. |
| `VISUAL_INSPECTION_DATA_GITHUB_RELEASE` | Text | No | `workshop-2026.08.15` | Immutable release tag for the workshop bundle. |
| `VISUAL_INSPECTION_DATA_SHA256` | Text | Yes | `c6f6b99f4cf239c6238cad510a90981f3b1ced11c7471280de4d3a7d387bcd19` | Pinned SHA-256 for the default workshop bundle. Replace it when selecting `full`. |
| `VISUAL_INSPECTION_DATA_VERSION` | Text | No | `2026.08.15` | Pins the immutable dataset bundle version. |
| `VISUAL_INSPECTION_DOCS_URL` | Text | No | `https://briandasantini.github.io/physical-ai-visual-inspection/` | Canonical participant guide linked from the app. |
| `VISUAL_INSPECTION_JUPYTER_URL` | Text | No | Auto-derived from `BREV_ENV_ID` | Optional explicit override for the Exercise 3 Jupyter terminal link. |

The repository retains private NGC and SharePoint download backends as fallbacks. Do not
configure them in the attendee Launchable.

## Access

- **Publish to community:** Off. Do not submit this workshop to the public Launchables
  catalog or the `brevdev/launchables` repository.
- **View access:** Use **Anyone with the link** for an external workshop, or **Only my
  organization** when every attendee belongs to the same Brev organization.
- Share the direct Launchable URL only with approved participants.

## Preflight

1. Accept the governing terms for both Cosmos Reason2 NIMs in NGC.
2. Publish the verified bundle under release tag `workshop-2026.08.15` in the private
   data repository.
3. Create a fine-grained token limited to Contents: Read-only on that repository.
4. Deploy once before the workshop so data hydration, model initialization, and image compatibility are proven.
5. Open the secure link and verify both default NIM status indicators are green and Nano is off.
6. Run one approved example with 8B and one with 2B.
7. Confirm neither setup logs nor container logs expose either credential.
8. Stop the rehearsal instance after validation to preserve credits.

## Agent access

Codex and Claude Code run directly in the Brev terminal and each prompts for provider
authentication on first use. Their credentials belong to the VM's Linux user and are
not launch parameters. Cursor and VS Code remain optional remote-SSH clients. Use one
VM or Linux account per participant if agent logins must remain separate.
Share `REMOTE_EDITORS.md` with participants who choose the remote-editor path.
