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


def test_ctrl_alt_letter_without_char_uses_vk_on_windows(monkeypatch) -> None:
  # 同時按住 Ctrl+Alt 時 Windows 不產生字元，只剩虛擬鍵碼（Z = 90）
  monkeypatch.setattr(events_module.sys, "platform", "win32")
  assert normalize_key(keyboard.KeyCode.from_vk(90)) == "z"
  assert normalize_key(keyboard.KeyCode.from_vk(ord("5"))) == "5"


def test_unmapped_vk_keeps_vk_label(monkeypatch) -> None:
  monkeypatch.setattr(events_module.sys, "platform", "win32")
  monkeypatch.setattr(events_module, "_windows_vk_to_layout_char", lambda vk: None)
  assert normalize_key(keyboard.KeyCode.from_vk(0x07)) == "vk_7"


def test_numpad_vk_maps_to_num_names_on_windows(monkeypatch) -> None:
  monkeypatch.setattr(events_module.sys, "platform", "win32")
  assert normalize_key(keyboard.KeyCode.from_vk(0x60)) == "num_0"
  assert normalize_key(keyboard.KeyCode.from_vk(0x69)) == "num_9"
  assert normalize_key(keyboard.KeyCode.from_vk(0x6B)) == "num_+"
  assert normalize_key(keyboard.KeyCode.from_vk(0x6E)) == "num_."


def test_display_label_for_numpad_keys() -> None:
  assert display_label("num_7") == "Num 7"
  assert display_label("num_/") == "Num /"


def test_ctrl_alt_symbol_key_uses_layout_char_on_windows(monkeypatch) -> None:
  monkeypatch.setattr(events_module.sys, "platform", "win32")
  monkeypatch.setattr(events_module, "_windows_vk_to_layout_char", lambda vk: {0xBA: ";", 0xDB: "["}.get(vk))
  assert normalize_key(keyboard.KeyCode.from_vk(0xBA)) == ";"


def test_ctrl_bracket_control_char_falls_back_to_vk(monkeypatch) -> None:
  # Ctrl+[ 會產生 ESC 控制字元 \x1b，不能直接顯示
  monkeypatch.setattr(events_module.sys, "platform", "win32")
  monkeypatch.setattr(events_module, "_windows_vk_to_layout_char", lambda vk: {0xDB: "["}.get(vk))
  assert normalize_key(keyboard.KeyCode(vk=0xDB, char="\x1b")) == "["


def test_windows_special_vk_has_readable_name(monkeypatch) -> None:
  monkeypatch.setattr(events_module.sys, "platform", "win32")
  assert normalize_key(keyboard.KeyCode.from_vk(0xA6)) == "browser_back"
  assert normalize_key(keyboard.KeyCode.from_vk(0x0C)) == "clear"


def test_display_label_keeps_num_lock_name() -> None:
  assert display_label("num_lock") == "num_lock"
