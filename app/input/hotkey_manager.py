"""追蹤目前按住的按鍵組合，判斷是否命中設定的熱鍵。"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal


def parse_hotkey(combo: str) -> frozenset[str]:
  """把 "<ctrl>+<alt>+l" 這種字串轉成正規化按鍵名稱集合，如 {"ctrl", "alt", "l"}。"""
  parts = [p.strip().strip("<>") for p in combo.split("+") if p.strip()]
  return frozenset(p.lower() for p in parts)


class HotkeyManager(QObject):
  hotkey_triggered = Signal()

  def __init__(self, combo: str, parent: QObject | None = None):
    super().__init__(parent)
    self._combo = parse_hotkey(combo)
    self._pressed: set[str] = set()
    self._armed = True  # 需完全放開組合鍵後才能再次觸發，避免持續按住時重複觸發

  def set_combo(self, combo: str) -> None:
    self._combo = parse_hotkey(combo)
    self._pressed.clear()
    self._armed = True

  def on_key_pressed(self, key: str) -> None:
    self._pressed.add(key.lower())
    if self._armed and self._combo and self._combo.issubset(self._pressed):
      self._armed = False
      self.hotkey_triggered.emit()

  def on_key_released(self, key: str) -> None:
    self._pressed.discard(key.lower())
    if not self._pressed:
      self._armed = True
