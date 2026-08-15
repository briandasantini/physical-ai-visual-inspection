# Work With an Agent

Codex and Claude Code are installed inside the Brev VM. The setup links a dedicated
`visual-inspection-workshop` skill into supported agent directories. Cursor and VS Code
can also connect over Brev-managed SSH.

## Start inside Brev

From the repository root:

```bash
codex
# or
claude
```

Each tool asks you to authenticate with your own provider account on first use.

Use this starting prompt:

```text
Read AGENT_CONTEXT.md, WORKSHOP_FLOW.md, CLI_GUIDE.md, and AGENTS.md.
Check visual inspection status, then guide me through the workshop one phase at a time.
Do not run inference until I record the expected label.
```

## What the agent knows

The repository instructions teach the agent to:

- use `./vision-inspect` rather than calling NIM endpoints directly;
- preserve the experiment order and labeled expectations;
- compare verdict correctness and explanation grounding separately;
- save generated JSON under `evidence/`;
- keep private images and credentials out of Git;
- ask before switching model sets or running a large batch;
- never treat model `PASS` as automated-run authorization.

## Editor path

Use `brev open` from your laptop to connect Cursor or VS Code. Open the repository root
so the editor agent can discover `AGENTS.md` and the workshop skill.

Do not clone the private dataset onto the laptop. All images remain mounted read-only in
the Brev environment.
