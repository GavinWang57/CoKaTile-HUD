"""測試按鍵 HUD 徽章的按住/連點/放開狀態轉換。"""
from __future__ import annotations

from PySide6.QtCore import QRect

from app.config import KeyHudConfig
from app.hud.key_hud_window import KeyHudWindow


def _make_window(qtbot) -> KeyHudWindow:
  window = KeyHudWindow(QRect(0, 0, 1920, 1080), KeyHudConfig())
  qtbot.addWidget(window)
  return window


def test_repeated_press_while_held_does_not_duplicate(qtbot) -> None:
  window = _make_window(qtbot)

  window.on_key_event_pressed("kb:a", "a")
  window.on_key_event_pressed("kb:a", "a")  # 模擬作業系統的按住自動重複事件

  assert len(window._badges) == 1
  assert window._badges[0].repeat_count == 1
  assert window._badges[0].released_at is None


def test_release_starts_fade_and_repress_counts_as_combo(qtbot) -> None:
  window = _make_window(qtbot)

  window.on_key_event_pressed("kb:a", "a")
  window.on_key_event_released("kb:a")
  assert window._badges[0].released_at is not None

  window.on_key_event_pressed("kb:a", "a")

  assert len(window._badges) == 1
  assert window._badges[0].repeat_count == 2
  assert window._badges[0].released_at is None


def test_different_keys_create_separate_badges(qtbot) -> None:
  window = _make_window(qtbot)

  window.on_key_event_pressed("kb:a", "a")
  window.on_key_event_pressed("kb:b", "b")

  assert len(window._badges) == 2


def test_release_unknown_key_is_noop(qtbot) -> None:
  window = _make_window(qtbot)

  window.on_key_event_released("kb:never-pressed")

  assert window._badges == []
