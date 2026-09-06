"""應用程式設定的資料結構與讀寫邏輯。"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from app.version import APP_NAME


def _default_find_cursor_hotkey() -> str:
  if sys.platform == "darwin":
    return "<cmd>+<alt>+l"
  return "<ctrl>+<alt>+l"


@dataclass
class SpotlightConfig:
  enabled: bool = True
  mode: str = "circle"  # "spotlight"（全螢幕暗化挖空）| "circle"（簡易色圈）
  color: str = "#FFFF00"
  radius: int = 45
  circle_opacity: float = 0.55  # circle 模式下色圈本身的透明度
  dim_opacity: float = 0.6  # spotlight 模式下背景暗化程度
  follow_smoothing: float = 0.3  # 0~1，越大跟隨越即時；顯示位置與實際游標的距離永遠不超過 radius


@dataclass
class ClickEffectConfig:
  enabled: bool = False
  left_color: str = "#00A2FF"
  right_color: str = "#FF4D4D"
  max_radius: int = 60
  duration_ms: int = 400


@dataclass
class KeyHudConfig:
  enabled: bool = False
  screen_index: int = -1  # -1 表示顯示在游標所在螢幕
  # "top/middle/bottom" + "left/center/right" 3x3 組合（如 "top-left"）、"center"，或 "follow_cursor"（動態跟隨游標）
  corner: str = "bottom-left"
  font_size: int = 20
  fade_duration_ms: int = 800
  max_visible_badges: int = 5
  show_mouse_buttons: bool = True


@dataclass
class FindCursorConfig:
  enabled: bool = True
  trigger_hotkey: str = field(default_factory=_default_find_cursor_hotkey)
  shake_detection_enabled: bool = True
  shake_min_reversals: int = 4
  shake_window_ms: int = 700
  shake_min_speed: float = 800.0
  effect_style: str = "pulse_circle"  # "crosshair" | "pulse_circle" | "both"
  effect_duration_ms: int = 2000
  play_sound: bool = False


@dataclass
class AppConfig:
  spotlight: SpotlightConfig = field(default_factory=SpotlightConfig)
  click_effect: ClickEffectConfig = field(default_factory=ClickEffectConfig)
  key_hud: KeyHudConfig = field(default_factory=KeyHudConfig)
  find_cursor: FindCursorConfig = field(default_factory=FindCursorConfig)
  active_profile: str = "daily"
  start_with_system: bool = False
  config_version: int = 1


_DEFAULTS = AppConfig()


def _load_sub(cls, data: dict, key: str):
  """依 dataclass 欄位還原子設定，缺項補預設值、忽略未知鍵，避免舊版設定檔讓整個載入失敗。"""
  sub = data.get(key)
  if not isinstance(sub, dict):
    return cls()
  valid_keys = {f.name for f in fields(cls)}
  filtered = {k: v for k, v in sub.items() if k in valid_keys}
  try:
    return cls(**filtered)
  except TypeError:
    return cls()


def config_from_dict(data: dict) -> AppConfig:
  if not isinstance(data, dict):
    return AppConfig()
  return AppConfig(
    spotlight=_load_sub(SpotlightConfig, data, "spotlight"),
    click_effect=_load_sub(ClickEffectConfig, data, "click_effect"),
    key_hud=_load_sub(KeyHudConfig, data, "key_hud"),
    find_cursor=_load_sub(FindCursorConfig, data, "find_cursor"),
    active_profile=data.get("active_profile", _DEFAULTS.active_profile),
    start_with_system=data.get("start_with_system", _DEFAULTS.start_with_system),
    config_version=data.get("config_version", _DEFAULTS.config_version),
  )


class ConfigManager:
  def __init__(self, path: Path | None = None):
    self._path = path or self.default_path()

  @staticmethod
  def default_path() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
    return Path(base) / APP_NAME / "settings.json"

  def load(self) -> AppConfig:
    if not self._path.exists():
      return AppConfig()
    try:
      raw = json.loads(self._path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
      return AppConfig()
    return config_from_dict(raw)

  def save(self, config: AppConfig) -> None:
    self._path.parent.mkdir(parents=True, exist_ok=True)
    self._path.write_text(
      json.dumps(asdict(config), ensure_ascii=False, indent=2),
      encoding="utf-8",
    )
