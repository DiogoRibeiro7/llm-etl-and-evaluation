"""Application entry points for llm_etl_eval."""

from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """Runtime configuration for the CLI."""

    verbose: bool


def parse_args(argv: list[str] | None = None) -> AppConfig:
    """Parse CLI arguments into an AppConfig instance."""

    parser = argparse.ArgumentParser(
        prog="llm-etl-eval",
        description="Utilities for LLM ETL and evaluation workflows.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output.",
    )
    args = parser.parse_args(argv)
    return AppConfig(verbose=bool(args.verbose))


def run(config: AppConfig) -> int:
    """Run the application logic.

    Returns a process exit code.
    """

    if config.verbose:
        print("llm_etl_eval: verbose mode enabled")
    else:
        print("llm_etl_eval: ready")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    config = parse_args(argv)
    return run(config)
