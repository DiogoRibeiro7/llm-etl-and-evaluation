"""CLI for writing a run manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

from llm_etl_eval.manifest.builder import (
    ManifestInputs,
    build_manifest,
    write_manifest,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="llm-etl-eval-manifest",
        description=(
            "Stamp a pipeline run with git state, config/schema/inputs "
            "hashes, and simulator settings."
        ),
    )
    parser.add_argument("--out", type=Path, required=True, help="Output manifest JSON path.")
    parser.add_argument("--config", type=Path, default=None, help="Pipeline config path.")
    parser.add_argument("--schema", type=Path, default=None, help="Target JSON schema path.")
    parser.add_argument("--inputs", type=Path, default=None, help="Processed inputs JSONL path.")
    parser.add_argument("--outputs", type=Path, default=None, help="LLM outputs JSONL path.")
    parser.add_argument("--gold", type=Path, default=None, help="Gold labels JSONL path.")
    parser.add_argument("--prompts", type=Path, default=None, help="Prompts JSONL path.")
    parser.add_argument("--seed", type=int, default=None, help="Simulator seed.")
    parser.add_argument(
        "--error-rate", type=float, default=None, help="Simulator error rate."
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Optional run id; defaults to a UTC timestamp.",
    )
    parser.add_argument(
        "--label",
        type=str,
        default=None,
        help="Free-form label (e.g., 'baseline', 'improved').",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    parser = build_parser()
    args = parser.parse_args(argv)

    manifest = build_manifest(
        ManifestInputs(
            config_path=args.config,
            schema_path=args.schema,
            inputs_path=args.inputs,
            outputs_path=args.outputs,
            gold_path=args.gold,
            prompts_path=args.prompts,
            seed=args.seed,
            error_rate=args.error_rate,
            run_id=args.run_id,
            label=args.label,
        )
    )
    write_manifest(manifest, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
