"""測試熱鍵組合偵測：需完全按下設定組合才觸發，且需放開後才能再次觸發。"""
from __future__ import annotations

from app.input.hotkey_manager import HotkeyManager, parse_hotkey


def test_parse_hotkey_normalizes_names() -> None:
  assert parse_hotkey("<ctrl>+<alt>+l") == frozenset({"ctrl", "alt", "l"})


def test_triggers_only_when_full_combo_pressed(qtbot) -> None:
  manager = HotkeyManager("<ctrl>+<alt>+l")
  triggered = []
  manager.hotkey_triggered.connect(lambda: triggered.append(True))

  manager.on_key_pressed("ctrl")
  manager.on_key_pressed("alt")
  assert triggered == []

  manager.on_key_pressed("l")
  assert len(triggered) == 1


def test_requires_full_release_before_retrigger(qtbot) -> None:
  manager = HotkeyManager("<ctrl>+<alt>+l")
  triggered = []
  manager.hotkey_triggered.connect(lambda: triggered.append(True))

  for key in ("ctrl", "alt", "l"):
    manager.on_key_pressed(key)
  assert len(triggered) == 1

  manager.on_key_pressed("l")  # 持續按住不應重複觸發
  assert len(triggered) == 1

  manager.on_key_released("l")
  manager.on_key_released("alt")
  manager.on_key_released("ctrl")

  for key in ("ctrl", "alt", "l"):
    manager.on_key_pressed(key)
  assert len(triggered) == 2


def test_left_right_modifiers_match_generic_combo(qtbot) -> None:
  # Windows 全域 hook 回報的是 ctrl_l / alt_l 等分左右的名稱
  manager = HotkeyManager("<ctrl>+<alt>+z")
  triggered = []
  manager.hotkey_triggered.connect(lambda: triggered.append(True))

  for key in ("ctrl_l", "alt_l", "z"):
    manager.on_key_pressed(key)
  assert len(triggered) == 1

  for key in ("z", "alt_l", "ctrl_l"):
    manager.on_key_released(key)
  for key in ("ctrl_r", "alt_gr", "z"):
    manager.on_key_pressed(key)
  assert len(triggered) == 2


def test_is_held_tracks_modifiers_across_left_right_names(qtbot) -> None:
  manager = HotkeyManager("<ctrl>+<alt>+z")
  manager.on_key_pressed("ctrl_l")
  assert manager.is_held("ctrl")
  manager.on_key_released("ctrl_l")
  assert not manager.is_held("ctrl")


def test_set_same_combo_keeps_pressed_keys(qtbot) -> None:
  # 每次套用設定都會呼叫 set_combo，組合沒變時不應忘記使用者仍按著的鍵
  manager = HotkeyManager("<ctrl>+<alt>+z")
  manager.on_key_pressed("ctrl_l")
  manager.set_combo("<ctrl>+<alt>+z")
  assert manager.is_held("ctrl")
  manager.set_combo("<ctrl>+<alt>+x")
  assert not manager.is_held("ctrl")
