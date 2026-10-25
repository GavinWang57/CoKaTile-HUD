"""滑鼠/鍵盤事件相關的按鍵名稱正規化與顯示文字轉換。"""
from __future__ import annotations

import ctypes
import sys

from pynput import keyboard

_CMD_KEY_NAMES = {"cmd", "cmd_l", "cmd_r"}

# Windows 數字鍵盤（NumLock 開啟時）的 VK 碼，pynput 不會產生字元，需自行對應
_WINDOWS_NUMPAD_VK_NAMES = {
  **{0x60 + n: f"num_{n}" for n in range(10)},
  0x6A: "num_*",
  0x6B: "num_+",
  0x6C: "num_,",
  0x6D: "num_-",
  0x6E: "num_.",
  0x6F: "num_/",
}

# pynput 的 Key 沒有涵蓋、也無法對應成字元的 Windows 特殊鍵
_WINDOWS_SPECIAL_VK_NAMES = {
  0x0C: "clear",  # NumLock 關閉時的數字鍵盤 5
  0x10: "shift",  # 不分左右的 Shift，遠端桌面或按鍵模擬軟體可能送出這個碼
  0x15: "ime_kana",
  0x16: "ime_on",
  0x17: "ime_junja",
  0x18: "ime_final",
  0x19: "ime_kanji",
  0x1A: "ime_off",
  0x1C: "ime_convert",
  0x1D: "ime_nonconvert",
  0x1E: "ime_accept",
  0x1F: "ime_mode_change",
  0x29: "select",
  0x2A: "print",
  0x2B: "execute",
  0x2F: "help",
  0x5F: "sleep",
  0xA6: "browser_back",
  0xA7: "browser_forward",
  0xA8: "browser_refresh",
  0xA9: "browser_stop",
  0xAA: "browser_search",
  0xAB: "browser_favorites",
  0xAC: "browser_home",
  0xB4: "launch_mail",
  0xB5: "launch_media",
  0xB6: "launch_app1",
  0xB7: "launch_app2",
  0xE5: "ime_process",
  0xF6: "attn",
  0xF7: "crsel",
  0xF8: "exsel",
  0xF9: "erase_eof",
  0xFA: "play",
  0xFB: "zoom",
  0xFD: "pa1",
  0xFE: "oem_clear",
}

_MAPVK_VK_TO_CHAR = 2
_MAPVK_DEAD_KEY_FLAG = 0x80000000


def _is_windows_alnum_vk(vk: int) -> bool:
  """Windows 的 VK 碼中，0~9 與 A~Z 恰好等於對應字元的 ASCII 碼。"""
  return ord("0") <= vk <= ord("9") or ord("A") <= vk <= ord("Z")


def _windows_vk_to_layout_char(vk: int) -> str | None:
  """依目前鍵盤配置取得按鍵未加 Shift 的字元（如 0xBA -> ";"），用於符號鍵。"""
  windll = getattr(ctypes, "windll", None)
  if windll is None:
    return None
  result = windll.user32.MapVirtualKeyW(vk, _MAPVK_VK_TO_CHAR)
  char = chr(result & ~_MAPVK_DEAD_KEY_FLAG & 0xFFFF) if result else ""
  return char if char.isprintable() and char.strip() else None


def _windows_vk_name(vk: int) -> str | None:
  if _is_windows_alnum_vk(vk):
    return chr(vk).lower()
  if vk in _WINDOWS_NUMPAD_VK_NAMES:
    return _WINDOWS_NUMPAD_VK_NAMES[vk]
  if vk in _WINDOWS_SPECIAL_VK_NAMES:
    return _WINDOWS_SPECIAL_VK_NAMES[vk]
  layout_char = _windows_vk_to_layout_char(vk)
  return layout_char.lower() if layout_char else None


def _printable_char(char: str | None) -> str | None:
  if not char:
    return None
  if len(char) == 1 and 1 <= ord(char) <= 26:
    # 按住 Ctrl 時，Windows/macOS 會把 KeyCode.char 轉成控制字元（如 Ctrl+C -> \x03）
    # 而不是按鍵本身的字母，還原成對應字母，避免顯示成無法呈現的方框字元
    return chr(ord(char) + 96)
  # 其餘控制字元（如 Ctrl+[ -> \x1b）無法直接顯示，交給虛擬鍵碼判斷
  return char if char.isprintable() else None


def normalize_key(key) -> str:
  """把 pynput 的 Key/KeyCode 物件轉成統一的字串表示，供 HUD 顯示與熱鍵比對共用。"""
  if isinstance(key, keyboard.KeyCode):
    char = _printable_char(key.char)
    if char is not None:
      return char.lower()
    if sys.platform == "win32" and key.vk is not None:
      # 同時按住 Ctrl+Alt、數字鍵盤或特殊鍵時 Windows 不會產生字元（char 為 None），改由虛擬鍵碼還原
      name = _windows_vk_name(key.vk)
      if name is not None:
        return name
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
  if key_id.startswith("num_") and key_id != "num_lock":
    return f"Num {key_id[len('num_'):]}"
  return key_id
