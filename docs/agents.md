# Work With Codex/Claude

Codex and Claude Code are installed inside the Brev VM. The setup links a dedicated
`visual-inspection-workshop` skill into both agent environments.

## Start inside Brev

Open the Jupyter terminal from **3 · Explore**, then run:

```bash
cd /home/nvidia/physical-ai-visual-inspection
codex
# or
claude
```

Each tool asks you to authenticate with your own provider account on first use.

Use this starting prompt:

```text
Read the workshop context and use the visual-inspection workshop skill. Help me explore
where 2B and 8B work, miss changes, or hallucinate; how contours affect verdict, action,
and object quality; which false-positive/false-negative trade-off and physical tolerance
matter for the intended workflow; which cases are missing; and what data would be needed
before fine-tuning. Propose one small investigation and explain what it would teach us.
```

## What the agent should help with

- inspect original model responses rather than only normalized summaries;
- compare verdict, action, object, location, hallucinations, and latency separately;
- run matched comparisons through `./vision-inspect`;
- connect precision and recall to real false-alarm and missed-change costs;
- define an ideal case, acceptable physical tolerance, and human-review boundary;
- identify missing objects, actions, nuisance conditions, and counterexamples;
- outline the positive, negative, boundary, nuisance, and held-out data needed next;
- preserve evidence and keep private images and credentials out of Git.

Dataset labels are reference annotations, not a quiz. The agent must not change labels to
match its own output. Unlabeled custom cases remain qualitative until a domain expert
defines a trustworthy policy.

Cursor and VS Code can also connect over Brev-managed SSH. Open the repository root so
the editor agent can discover `AGENTS.md` and the workshop skill. Do not copy the private
dataset onto the laptop.
