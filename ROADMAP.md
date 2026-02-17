# Roadmap

## Now (0-2 weeks)

- Stabilize the demo scripts and configs as the default interview flow.
- Add contract-based validation coverage for `LLMOutputRecord`.
- Expand round-trip payload checks with a minimal “API error simulator”.

## Next (2-6 weeks)

- Add dataset connectors (CSV/JSONL/S3) with clear schema mapping.
- Add prompt + schema versioning and a run manifest per experiment.
- Introduce drift checks for key semantic fields (category/priority/language).

## Later (6-12 weeks)

- Integrate a real LLM provider and capture latency/cost metrics.
- Add robust error clustering with automatic remediation suggestions.
- Build a lightweight UI for report diffs and regression triage.
