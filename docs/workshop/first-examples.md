# 1. First Examples

Use the curated pairs to discover how 2B and 8B reason—not to predict the dataset label.
The set introduces a matching setup, removal, larger configuration change, unexpected
object, and subtle displacement.

## Browser exploration

1. Open **1 · First Examples** and load a pair.
2. Treat the displayed dataset label as a reference annotation.
3. Run **A · Run baseline** and read each original model response.
4. Ask what physical evidence is correct, missing, uncertain, or invented.
5. Separate verdict quality from action, object, and location quality.
6. Compare how 2B and 8B reason about the same images.
7. Run **B · Run with contours** and ask what changed—not only whether the verdict changed.

## What to notice

| Lens | Question |
|---|---|
| Model strength | What kind of physical change does the model describe reliably? |
| Miss | What visible change does it overlook? |
| Hallucination | What object, action, or location does it invent? |
| Semantics | Is the verdict right but the action or object wrong? |
| Model size | Do 2B and 8B fail differently on the same case? |
| Cue effect | Does the contour help attention, distort meaning, or create a false alarm? |
| Coverage | What new object, action, nuisance condition, or counterexample does this suggest? |

!!! tip
    Review the whole original response. A normalized summary can hide uncertainty,
    contradiction, or hallucinated details that matter more than the verdict.

Finish by naming one observed strength, one failure pattern, and one case you wish the
dataset contained.
