"""Tests for the application entry points."""

from __future__ import annotations

from pytest import CaptureFixture

from llm_etl_eval.app import AppConfig, parse_args, run


def test_parse_args_defaults() -> None:
    config = parse_args([])
    assert config == AppConfig(verbose=False)


def test_run_verbose_output(capsys: CaptureFixture[str]) -> None:
    exit_code = run(AppConfig(verbose=True))
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "verbose mode enabled" in captured.out
