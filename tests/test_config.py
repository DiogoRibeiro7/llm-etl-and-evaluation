"""Tests for pipeline config loading."""

from __future__ import annotations

from pathlib import Path

from llm_etl_eval.config import load_config


def test_load_config_from_yaml(tmp_path: Path) -> None:
    content = """
coercion:
  enabled: false
parsing:
  strict: true
prompt:
  strictness: strict
  schema_reminders: true
""".lstrip()
    path = tmp_path / "config.yaml"
    path.write_text(content, encoding="utf-8")

    config = load_config(path)
    assert config.coercion_enabled is False
    assert config.strict_parsing is True
    assert config.prompt_strictness == "strict"
    assert config.schema_reminders is True
