# Facilitator Guide

## Before sharing the Launchable

1. Confirm the public repository contains code and documentation only.
2. Upload and pin the approved private GitHub Release asset and checksum.
3. Confirm the Cosmos NIM terms have been accepted for the workshop organization.
4. Provision a fine-grained Contents: Read-only token for the private data repository.
5. Deploy a new two-GPU instance from the final Launchable.
6. Wait for both default NIMs and the website to become ready.
7. Run one `PASS` pair and one `FAIL` pair with both 2B and 8B.
8. Verify that the dataset is read-only and no key appears in logs.
9. Stop the rehearsal instance after validation.

## Suggested run of show

| Segment | Time |
|---|---:|
| Context, safety boundary, and experiment question | 10 min |
| Curated first examples | 25 min |
| Larger labeled sample | 35 min |
| Matched contour-assisted rerun | 30 min |
| Findings and post-training data plan | 20 min |

## Facilitation prompts

- What did you expect before seeing the model response?
- Is the verdict correct for the right reason?
- Which statement in the explanation is directly supported by pixels?
- Did the contour input help the model or merely change its confidence?
- What negative examples would prevent this false alarm?
- What held-out test would prove that post-training helped?

## Closing decision

End with a decision for each important category:

- use as-is for further evaluation;
- combine with conventional vision cues;
- collect more labeled data;
- post-train a selected model;
- retain a human or deterministic control.

Never hide misses or hallucinations behind an aggregate score.
