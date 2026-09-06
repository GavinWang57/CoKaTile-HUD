"""滑鼠/鍵盤事件相關的按鍵名稱正規化與顯示文字轉換。"""
from __future__ import annotations

import sys

from pynput import keyboard

_CMD_KEY_NAMES = {"cmd", "cmd_l", "cmd_r"}


def normalize_key(key) -> str:
  """把 pynput 的 Key/KeyCode 物件轉成統一的字串表示，供 HUD 顯示與熱鍵比對共用。"""
  if isinstance(key, keyboard.KeyCode):
    if key.char:
      char = key.char
      if len(char) == 1 and 1 <= ord(char) <= 26:
        # 按住 Ctrl 時，Windows/macOS 會把 KeyCode.char 轉成控制字元（如 Ctrl+C -> \x03）
        # 而不是按鍵本身的字母，還原成對應字母，避免顯示成無法呈現的方框字元
        char = chr(ord(char) + 96)
      return char.lower()
    return f"vk_{key.vk}"
  if isinstance(key, keyboard.Key):
    return key.name
  return str(key)


def display_label(key_id: str) -> str:
  """把 normalize_key() 的內部識別字串轉成適合顯示的文字。

  pynput 統一用 "cmd"（及 cmd_l/cmd_r）代表 Windows 鍵與 macOS 的 Command 鍵，
  這裡依作業系統換成使用者熟悉的名稱；其餘按鍵維持原樣，識別用的內部字串不受影響。
  """
  if key_id in _CMD_KEY_NAMES:
    return "Cmd" if sys.platform == "darwin" else "Win"
  return key_id
