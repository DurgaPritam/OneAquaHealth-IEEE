# Vision eval: mock (mock-deterministic-1)

Run 2026-09-26 with `python -m eval.run_vision_eval`.

## Limits first

- **Synthetic inputs.** These are generated test cards, not photos. `"synthetic": true`.
- **Mock provider.** It picks a label by hashing the image bytes and never looks at pixels. Agreement here measures nothing about AI accuracy; it only proves the pipeline, the validation gate and the metrics work end to end.
- Human labels are the reference. No AI output is ever used as a reference label.

## Results

| Metric | Value |
|---|---|
| Items | 26 |
| Provider available | 1.00 |
| Agreement with human label (excluding not sure) | 0.15 |
| Not-sure rate | 0.00 |
| Dropped labels per photo (validation gate) | 0.15 |
| Mean confidence when right | 0.76 |
| Mean confidence when wrong | 0.73 |
| Latency p50 / p95 (ms) | 0.00 / 0.00 |
| Cost | n/a (mock or unknown model) |

## How to run on real photos

Put licensed photos in a folder with `labels.csv` (file, finding_type, human_label, licence, source), then:

```
AI_PROVIDER=anthropic ANTHROPIC_API_KEY=... .venv/bin/python -m eval.run_vision_eval --folder path/to/photos
```
