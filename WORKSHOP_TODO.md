# Workshop TODO

Capture improvements discovered during participant rehearsals without changing the
running workshop mid-test. Review, prioritize, and implement these after each complete
walkthrough.

## Content

- [x] Remove the participant-facing automated-run warning from the web app, docs, and
  agent skill.
- [x] Add a short Cosmos introduction to the workshop starting point:
  - what NVIDIA Cosmos is;
  - why a reasoning vision model is being evaluated for visual inspection;
  - what the workshop is testing rather than claiming as a finished solution;
  - why participants compare baseline reasoning with pixel-level contour cues;
  - where Reason2 8B, Reason2 2B, and optional Nano fit in the evaluation.
  - use the concise, expandable `NVIDIA Cosmos VLMs` introduction from
    the latest local evaluation report as the content and visual
    reference;
  - distinguish Cosmos Reason2 from Cosmos3, explain that the workshop uses the
    Cosmos3 Nano Reasoner rather than its generator, and keep the level accessible to
    participants who are new to both model families.

## Participant Experience

- [x] Replace the remaining orange Gradio accents—including active tabs, links, and
  selection highlights—with NVIDIA green for a consistent workshop theme.
- [x] Make the agent-guided workshop the recommended participant path, while retaining
  the website-only path as an alternative. Design for one designated agent driver per
  team environment.
- [x] Add an `Agent Guide` to the tutorial with copyable prompts for every stage. Each
  stage should tell the agent to explain its plan, show the supported `vision-inspect`
  command it runs, interpret the evidence, identify uncertainty, and propose the next
  question rather than merely returning a verdict.
- [x] Structure the agent prompts around the full learning flow:
  - orient to Cosmos, the experiment, the dataset, and model readiness;
  - predict and run the curated baseline examples;
  - audit whether the verdict and explanation are both grounded;
  - compare Reason2 2B and 8B on the same evidence;
  - rerun the same examples with contour assistance and explain what changed;
  - sample the larger labeled set and identify recurring success and failure modes;
  - design a controlled contour experiment;
  - decide what post-training data would be needed and which model is the best candidate.
- [x] Include suggested questions beside each agent prompt, such as what visual evidence
  supports the answer, what the model may have invented, whether the contour changed the
  verdict or only the explanation, and what additional example would falsify the current
  hypothesis.
- [x] Add supported CLI controls for contour experiments before asking agents to vary
  them. At minimum expose pixel threshold and minimum contour area, record their values
  in JSON evidence, and provide safe agent prompts for comparing fixed settings on the
  same pair. Consider additional visual-cue algorithms only after the basic sweep is
  reliable.
- [ ] Separate one-click Launchable instructions from manual VM setup so beginners are
  not asked for `VISUAL_INSPECTION_DATA_SHA256` or shell setup commands unnecessarily.
- [ ] Review the Launchable content preview as a first-time participant and make the
  intended first action unmistakable.

## Rehearsal Notes

- [x] Complete one clean deployment from the organization-only Launchable.
- [ ] Validate access with a second workshop-organization member: Launchable visibility, workspace
  sharing, secure-link login, Jupyter access, and SSH permissions. Document the exact
  invitation and pre-workshop sign-in steps so participants authenticate before the
  hands-on session starts.
- [x] Complete an automated website rehearsal covering all five curated pairs with both
  models, baseline and contour runs, comparisons and exports; a ten-pair larger-set run;
  progress tracking; dataset search; and exploration-mode inference and export.
- [ ] Complete the website tutorial manually as a first-time participant and record
  confusing wording, navigation, and guided moments.
- [x] Complete the supported CLI tutorial from the Brev shell and save rehearsal evidence.
- [ ] Repeat the CLI tutorial from a Jupyter terminal during the human walkthrough.
- [ ] Rehearse the new integrated agent terminal, including first-time Codex and Claude
  sign-in, persistent terminal home, one complete cue sweep, and gateway reconnect behavior.
- [x] Record initial setup duration, model readiness, inference latency, and findings.

### 2026-08-16 automated rehearsal

- Cold Launchable deployment took approximately 30 minutes from deployment to a usable
  participant site with both Reason2 NIMs ready.
- Post-rehearsal health was clean: Reason2 2B, Reason2 8B, and the participant site were
  healthy; the website returned HTTP 200; Jupyter returned its expected redirect; Nano
  `1.7.0` was installed and off; and the workshop skill resolved for Codex, Claude, and
  generic agents.
- The CLI required flow completed in approximately 27 seconds once warm. Individual NIM
  calls were approximately 0.1–1.0 seconds during this rehearsal.
- Reason2 8B got 2/5 curated baseline verdicts correct. Contours recovered one removal,
  producing 3/5 correct, but the foreign-object and subtle-tilt examples remained misses.
- On the ten-pair Shift/Displace sample, 8B baseline verdict accuracy was 0% and contour
  verdict accuracy was 100%. The contour explanations often described shifts as added or
  replaced objects, so verdict correctness must not be presented as grounded reasoning.
- On the subtle-tilt comparison, 2B returned `UNKNOWN` at baseline and `FAIL` with contours
  while mischaracterizing the change; 8B returned `PASS` in both modes.
- The full automated website route rehearsal took approximately three minutes and
  successfully exercised all participant actions and JSON downloads.
- Local validation passed all 29 unit tests and built the Gradio interface successfully.
- Use `./vision-inspect status` for participant health checks. A raw `docker compose ps`
  from a fresh interactive shell requires the NGC environment variable for Compose file
  interpolation even when the already-running containers are healthy.

### 2026-08-16 prompt and agent-terminal revision

- Shared, pair-agnostic prompt trials were run across all five curated examples. The
  selected inventory-and-verification prompt produced no `UNKNOWN` verdicts: Reason2 2B
  reached 4/5 baseline verdicts and Reason2 8B reached 3/5, while preserving useful misses.
- With matched default contours, 2B reached 5/5 verdicts but still misidentified several
  actions or items; 8B remained 3/5. This confirms that verdict accuracy and semantic
  grounding must remain separate workshop metrics.
- A real 8B `r1_tilt` sweep validated the new CLI path. Baseline returned `PASS`; color
  difference at threshold 25/minimum area 3000 returned the correct `FAIL` but scored wrong
  on both action and item; edge difference returned `PASS`. Total latency was 0.74s,
  0.61s, and 0.37s respectively on the warm rehearsal instance.
- Thirteen shared prompt variants were benchmarked across both models and all five curated
  pairs, followed by three-repeat stability tests of the strongest candidates. The selected
  concise taxonomy prompt produced 60% repeated verdict accuracy for both models. Reason2
  2B had 75% precision and 75% recall; Reason2 8B had 100% precision and 50% recall.
- The apparent 2B advantage under some prompts came from a FAIL-heavy five-pair set and a
  tendency to over-call FAIL. The 8B model was more conservative, producing fewer false
  alarms but missing the small foreign tool and subtle tilt. The selected prompt balances
  those behaviors rather than preserving an unstable single-run 5/5 result.
- The curated images are only 400 by 266 pixels. Prompt changes cannot recover absent visual
  detail, so the remaining small-object and subtle-orientation failures are intentionally
  carried into the contour and post-training discussion.
- The final participant-path rehearsal with the selected prompt produced 60% baseline and
  60% contour verdict accuracy for Reason2 8B, versus 40% baseline and 80% contour accuracy
  for Reason2 2B in that single run. Neither model grounded the expected action and item
  reliably. This run-to-run variation is evidence to show, not a score to optimize away.
- Docker Compose configuration, UI image, terminal image, Nginx gateway, `/terminal/`
  proxy, and direct CLI were validated on Brev in isolated temporary containers.
- The non-root terminal installed `codex-cli 0.147.0` and Claude Code `2.1.224`, then
  served ttyd successfully. Temporary validation containers were removed afterward.
- Local validation passed all 37 unit tests and built the Gradio interface successfully.
