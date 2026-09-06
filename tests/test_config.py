"""測試設定的儲存/讀取 round-trip 與相容性。"""
from __future__ import annotations

from pathlib import Path

from app.config import AppConfig, ConfigManager, SpotlightConfig, config_from_dict


def test_save_and_load_round_trip(tmp_path: Path) -> None:
  manager = ConfigManager(path=tmp_path / "settings.json")
  original = AppConfig(spotlight=SpotlightConfig(enabled=False, color="#123456", radius=99))

  manager.save(original)
  loaded = manager.load()

  assert loaded == original


def test_load_missing_file_returns_defaults(tmp_path: Path) -> None:
  manager = ConfigManager(path=tmp_path / "does_not_exist.json")
  assert manager.load() == AppConfig()


def test_load_ignores_unknown_and_missing_fields() -> None:
  raw = {
    "spotlight": {"enabled": False, "unknown_field": "x"},
    "unrelated_top_level_field": 123,
  }
  config = config_from_dict(raw)

  assert config.spotlight.enabled is False
  assert config.spotlight.radius == SpotlightConfig().radius
  assert config.click_effect == AppConfig().click_effect
