# 2. Larger Set

The curated examples reveal failure modes; the larger labeled set tests whether those
observations generalize.

## Choose the sample before inference

1. Open **2 · Larger Set**.
2. Choose a category and a fixed sample size.
3. Use one model, beginning with Cosmos Reason2 8B.
4. Record the category, count, and expected class balance.
5. Run **A · Run larger-set baseline**.

Keep an interactive batch to roughly ten pairs unless the facilitator approves a larger
run. Every pair invokes a NIM.

## Read the metrics

The workshop treats `FAIL` as the positive class.

- **Accuracy:** overall fraction of correct verdicts.
- **Precision:** how often a predicted difference is real.
- **Recall:** how many labeled differences the model detects.
- **F1:** balance between precision and recall.
- **Action %:** among correctly predicted `FAIL` cases with action labels, how often the
  response names the expected change type.
- **Item %:** among those eligible cases, how often the response names the expected item.
- **Latency:** NIM inference, contour preprocessing, total, and p95 total response time.

Metrics are only the start. Review every incorrect row and classify the failure:

- missed physical change;
- false alarm on a matching setup;
- correct verdict with incorrect explanation;
- ambiguous or unsupported reasoning;
- category-specific weakness such as subtle displacement.

Open the representative raw outputs under each run. They include a correct result, a miss
when available, and another contrasting case so the aggregate metrics remain interpretable.

## Required output

Export the baseline evidence and write one sentence:

> On this fixed sample, the strongest category was ___, the weakest category was ___,
> and the most important reasoning failure was ___.
