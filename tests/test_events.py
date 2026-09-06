"""測試按鍵正規化與顯示文字轉換：Ctrl+字母控制字元還原、Windows/Mac 的 cmd 鍵顯示名稱。"""
from __future__ import annotations

from pynput import keyboard

import app.input.events as events_module
from app.input.events import display_label, normalize_key


def test_ctrl_letter_control_char_normalizes_back_to_letter() -> None:
  # 按住 Ctrl 時，Windows 會把 KeyCode.char 轉成控制字元（Ctrl+C -> \x03），而非字母 "c"
  ctrl_c = keyboard.KeyCode(char="\x03")
  assert normalize_key(ctrl_c) == "c"


def test_ctrl_a_control_char_normalizes_to_a() -> None:
  ctrl_a = keyboard.KeyCode(char="\x01")
  assert normalize_key(ctrl_a) == "a"


def test_regular_letter_key_unaffected() -> None:
  key = keyboard.KeyCode(char="c")
  assert normalize_key(key) == "c"


def test_uppercase_letter_key_lowercased() -> None:
  key = keyboard.KeyCode(char="C")
  assert normalize_key(key) == "c"


def test_named_special_key_uses_pynput_name() -> None:
  assert normalize_key(keyboard.Key.enter) == "enter"
  assert normalize_key(keyboard.Key.ctrl) == "ctrl"


def test_display_label_shows_win_on_windows(monkeypatch) -> None:
  monkeypatch.setattr(events_module.sys, "platform", "win32")
  assert display_label("cmd") == "Win"
  assert display_label("cmd_l") == "Win"
  assert display_label("cmd_r") == "Win"


def test_display_label_shows_cmd_on_macos(monkeypatch) -> None:
  monkeypatch.setattr(events_module.sys, "platform", "darwin")
  assert display_label("cmd") == "Cmd"


def test_display_label_passthrough_for_other_keys() -> None:
  assert display_label("a") == "a"
  assert display_label("ctrl") == "ctrl"
