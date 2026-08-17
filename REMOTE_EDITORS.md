# Optional Cursor or VS Code access

The browser workshop does not require an editor. Use this path only if you want an
editor or coding agent to work directly against the files and GPUs on the Brev VM.

## Before the workshop

Install these on your **local laptop**, not inside Brev:

1. The NVIDIA Brev CLI, then sign in to the organization that owns the instance.
2. One editor:
   - VS Code with the **Remote - SSH** extension and the `code` command in `PATH`.
   - Cursor with the `cursor` command in `PATH`.

Confirm that the instance is visible:

```bash
brev login
brev org ls
brev org set <workshop-org>
brev ls
```

Use the `<workshop-org>` name provided for the workshop.

## Open the remote repository

Run one command from your **local laptop**, replacing `<instance-name>` with the name
shown by `brev ls`:

```bash
# VS Code
brev open <instance-name> code \
  --dir /home/nvidia/workspace/physical-ai-visual-inspection/physical-ai-visual-inspection

# Cursor
brev open <instance-name> cursor \
  --dir /home/nvidia/workspace/physical-ai-visual-inspection/physical-ai-visual-inspection
```

Brev manages the SSH connection. Do not clone or copy the dataset to the laptop.

## Start working

Open the editor's integrated terminal. It should be a remote Brev shell in the
`physical-ai-visual-inspection` repository:

```bash
pwd
./vision-inspect status
```

Choose one agent interface:

- Use Cursor Agent or GitHub Copilot in the remote editor. The repository's
  `AGENTS.md` or `.github/copilot-instructions.md` supplies the workshop guardrails.
- Run `codex` or `claude` in the integrated terminal. Both are already installed in
  Brev and prompt for personal authentication on first use.

Start with this prompt:

```text
Read AGENT_CONTEXT.md, WORKSHOP_FLOW.md, CLI_GUIDE.md, and AGENTS.md. Check visual inspection
status, then help me explore where the models work, miss changes, or hallucinate. Compare
verdict, action, object, and contour effects; ask what false-positive/false-negative trade-off
and physical tolerance matter for the intended workflow; and identify missing cases and
data needed before fine-tuning.
```

## Troubleshooting

- **Editor command not found:** install the editor's shell command, then reopen the
  local terminal.
- **Instance not found:** run `brev org ls`, switch with
  `brev org set <workshop-org>`, and run `brev ls` again.
- **Editor does not connect:** run `brev refresh`, then retry `brev open`.
- **Wrong folder:** use **File → Open Folder** and enter the remote path shown above.
- **Agent ignores the workflow:** confirm the editor opened the repository root and
  ask it to read `AGENTS.md` before continuing.

Closing the editor only closes SSH; it does not stop the paid Brev instance. Stop the
instance in Brev after the workshop. Agent credentials are stored for the Brev Linux
user, so do not sign multiple personal accounts into one shared VM user.

Official references: [NVIDIA Brev connectivity](https://docs.nvidia.com/brev/cli/connectivity),
[VS Code Remote SSH](https://code.visualstudio.com/docs/remote/ssh), and
[Cursor documentation](https://cursor.com/docs).
