# 3. Explore With Codex/Claude

Use the Jupyter terminal to investigate one open question raised by the evidence. A
contour sweep is one option, not the definition of the exercise.

## Start the conversation

```text
Read the workshop context and use the visual-inspection workshop skill. Help me explore
where 2B and 8B work, miss changes, or hallucinate; how contours affect verdict, action,
and object quality; which error trade-off and physical tolerance matter for the intended
workflow; which cases are missing; and what data would be needed before fine-tuning.
Propose one small investigation and explain what its result would mean.
```

## Short directions to explore

- “Show me where 2B and 8B reason differently on the same cases.”
- “Find one recurring hallucination or semantic error.”
- “Does the contour improve detection but hurt action or object quality?”
- “Which is more costly here: a false alarm or a missed change?”
- “What physical deviation should be acceptable or sent to human review?”
- “Which object, action, nuisance condition, or edge case is missing?”
- “What positive, negative, nuisance, and held-out data would fine-tuning require?”

## If you choose a contour experiment

Keep the model, prompt, and pair fixed while varying one cue factor:

```bash
./vision-inspect sweep --pair <pair-id> --model reason2-8b \
  --diff-methods color channel-max edges \
  --thresholds 15 25 35 --min-areas 3000 \
  --output evidence/cue-sweep.json
```

Compare verdict, action, object, hallucinations, contour regions, changed-pixel ratio,
preprocessing latency, NIM latency, and total latency. Explain whether the cue improved
the physical understanding or merely changed the answer.

## Turn findings into a requirements and data plan

Before recommending fine-tuning, describe:

1. the intended inspection case and operational decision;
2. the objects, actions, and locations that matter;
3. acceptable displacement, angle, occupancy, or appearance tolerance;
4. the relative cost of false positives and false negatives;
5. missing positive, negative, boundary, and nuisance examples;
6. ambiguous cases that need domain-expert labeling;
7. scene-disjoint validation and untouched held-out tests;
8. the current baseline that future work must beat without worse hallucination or semantics.

The next step may be clearer requirements, better captures, conventional vision, prompt
work, or fine-tuning. The workshop should discover which—not assume the answer in advance.
