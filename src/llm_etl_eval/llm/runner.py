"""Drive an LLM provider over a prompt set and persist outputs + telemetry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm_etl_eval.llm.provider import LLMProvider


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _try_parse_json(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _serialize_output_line(text: str) -> str:
    """Emit a single JSONL line for the model's output.

    If the text is already valid JSON, normalize it to compact form.
    Otherwise collapse newlines so the tolerant transform parser can
    still pick up embedded JSON or fail with a clean parse error.
    """

    parsed = _try_parse_json(text)
    if parsed is not None:
        return json.dumps(parsed, sort_keys=True)
    return text.replace("\r", "").replace("\n", " ").strip()


def run_llm(
    inputs_path: Path,
    prompts_path: Path,
    outputs_path: Path,
    telemetry_path: Path,
    provider: LLMProvider,
    *,
    max_records: int | None = None,
) -> None:
    """Run the provider over input/prompt pairs and write JSONL artifacts.

    Inputs and prompts must be aligned by index. The output is shaped
    identically to the simulator so the rest of the pipeline (transform,
    eval, drift, clusters) sees a consistent format.
    """

    inputs = _load_jsonl(inputs_path)
    prompts = _load_jsonl(prompts_path)
    if len(inputs) != len(prompts):
        raise ValueError(
            f"Length mismatch: inputs={len(inputs)}, prompts={len(prompts)}"
        )

    if max_records is not None:
        inputs = inputs[:max_records]
        prompts = prompts[:max_records]

    outputs_path.parent.mkdir(parents=True, exist_ok=True)
    telemetry_path.parent.mkdir(parents=True, exist_ok=True)

    with (
        outputs_path.open("w", encoding="utf-8") as out_f,
        telemetry_path.open("w", encoding="utf-8") as tel_f,
    ):
        for record, prompt in zip(inputs, prompts, strict=True):
            ticket_id = record.get("ticket_id", "unknown")
            response = provider.complete(
                system=str(prompt.get("system", "")),
                user=str(prompt.get("user", "")),
            )

            out_f.write(_serialize_output_line(response.text) + "\n")

            tel_f.write(
                json.dumps(
                    {
                        "ticket_id": ticket_id,
                        "latency_ms": response.latency_ms,
                        "input_tokens": response.input_tokens,
                        "output_tokens": response.output_tokens,
                        "model": response.model,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
