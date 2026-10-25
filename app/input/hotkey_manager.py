"""追蹤目前按住的按鍵組合，判斷是否命中設定的熱鍵。"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

# Windows 的全域 hook 回報的是分左右的修飾鍵（如 ctrl_l），熱鍵設定只寫 <ctrl>，比對前需統一
_MODIFIER_ALIASES = {
  "ctrl_l": "ctrl",
  "ctrl_r": "ctrl",
  "alt_l": "alt",
  "alt_r": "alt",
  "alt_gr": "alt",
  "shift_l": "shift",
  "shift_r": "shift",
  "cmd_l": "cmd",
  "cmd_r": "cmd",
}


def _canonical_key(key: str) -> str:
  key = key.lower()
  return _MODIFIER_ALIASES.get(key, key)


def parse_hotkey(combo: str) -> frozenset[str]:
  """把 "<ctrl>+<alt>+l" 這種字串轉成正規化按鍵名稱集合，如 {"ctrl", "alt", "l"}。"""
  parts = [p.strip().strip("<>") for p in combo.split("+") if p.strip()]
  return frozenset(_canonical_key(p) for p in parts)


class HotkeyManager(QObject):
  hotkey_triggered = Signal()

  def __init__(self, combo: str, parent: QObject | None = None):
    super().__init__(parent)
    self._combo = parse_hotkey(combo)
    self._pressed: set[str] = set()
    self._armed = True  # 需完全放開組合鍵後才能再次觸發，避免持續按住時重複觸發

  def set_combo(self, combo: str) -> None:
    new_combo = parse_hotkey(combo)
    if new_combo == self._combo:
      # 每次套用設定都會呼叫；組合沒變時保留目前按住的鍵，避免使用者仍按著 Ctrl 卻被當成已放開
      return
    self._combo = new_combo
    self._pressed.clear()
    self._armed = True

  def is_held(self, key: str) -> bool:
    return _canonical_key(key) in self._pressed

  def on_key_pressed(self, key: str) -> None:
    self._pressed.add(_canonical_key(key))
    if self._armed and self._combo and self._combo.issubset(self._pressed):
      self._armed = False
      self.hotkey_triggered.emit()

  def on_key_released(self, key: str) -> None:
    self._pressed.discard(_canonical_key(key))
    if not self._pressed:
      self._armed = True
