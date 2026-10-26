"""包裝 pynput 的全域滑鼠/鍵盤監聽，透過 Qt signal 安全送回主執行緒。"""
from __future__ import annotations

import ctypes
import sys
import threading

from PySide6.QtCore import QObject, QTimer, Signal
from pynput import keyboard, mouse

from app.input.events import normalize_key
from app.platform.screen_utils import capture_screen_dpi_info, physical_to_logical_point

_BUTTON_NAMES = {
  mouse.Button.left: "left",
  mouse.Button.right: "right",
  mouse.Button.middle: "middle",
}

_STUCK_KEY_CHECK_INTERVAL_MS = 500
_ASYNC_KEY_DOWN_FLAG = 0x8000


def _key_vk(key) -> int | None:
  if isinstance(key, keyboard.KeyCode):
    return key.vk
  if isinstance(key, keyboard.Key):
    return getattr(key.value, "vk", None)
  return None


def _is_vk_physically_down(vk: int) -> bool:
  return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & _ASYNC_KEY_DOWN_FLAG)


class GlobalInputListener(QObject):
  mouse_moved = Signal(int, int)
  mouse_pressed = Signal(int, int, str)
  mouse_released = Signal(int, int, str)
  key_pressed = Signal(str)
  key_released = Signal(str)
  listener_error = Signal(str)

  def __init__(self, parent: QObject | None = None):
    super().__init__(parent)
    self._mouse_listener: mouse.Listener | None = None
    self._keyboard_listener: keyboard.Listener | None = None
    self._screen_dpi_info: list[tuple[int, int, int, int, float]] = []
    self._held_key_vks: dict[str, int] = {}
    self._held_key_lock = threading.Lock()
    self._stuck_key_timer = QTimer(self)
    self._stuck_key_timer.setInterval(_STUCK_KEY_CHECK_INTERVAL_MS)
    self._stuck_key_timer.timeout.connect(self._release_stuck_keys)
    if sys.platform == "win32":
      # 鎖定畫面（安全桌面）上 hook 收不到事件，解鎖時最後一個按鍵的放開事件會遺失，需定期比對實際按鍵狀態
      self.key_pressed.connect(self._ensure_stuck_key_timer)

  def start(self) -> None:
    # 在主執行緒擷取一次螢幕 DPI 資訊，讓背景 hook 執行緒能安全換算座標，不必直接呼叫 Qt API
    self.refresh_screen_dpi_info()
    try:
      self._mouse_listener = mouse.Listener(on_move=self._on_move, on_click=self._on_click)
      self._keyboard_listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
      self._mouse_listener.start()
      self._keyboard_listener.start()
    except Exception as exc:  # 轉成 signal，讓上層（例如 macOS 權限提示）決定如何處理
      self.listener_error.emit(str(exc))

  def stop(self) -> None:
    if self._mouse_listener is not None:
      self._mouse_listener.stop()
      self._mouse_listener = None
    if self._keyboard_listener is not None:
      self._keyboard_listener.stop()
      self._keyboard_listener = None
    self._stuck_key_timer.stop()

  def refresh_screen_dpi_info(self) -> None:
    """螢幕解析度/縮放或多螢幕組態改變時（如接上/拔除螢幕）呼叫，更新座標換算依據。"""
    self._screen_dpi_info = capture_screen_dpi_info()

  def _to_logical(self, x: int, y: int) -> tuple[int, int]:
    return physical_to_logical_point(x, y, self._screen_dpi_info)

  def _on_move(self, x: int, y: int) -> None:
    logical_x, logical_y = self._to_logical(x, y)
    self.mouse_moved.emit(logical_x, logical_y)

  def _on_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
    logical_x, logical_y = self._to_logical(x, y)
    # 側鍵（x1/x2）只有 Windows/Linux 版 pynput 才有定義，用列舉名稱取得，避免 macOS 上存取不存在的屬性
    name = _BUTTON_NAMES.get(button, getattr(button, "name", str(button)))
    if pressed:
      self.mouse_pressed.emit(logical_x, logical_y, name)
    else:
      self.mouse_released.emit(logical_x, logical_y, name)

  def _on_press(self, key) -> None:
    name = normalize_key(key)
    vk = _key_vk(key)
    if vk is not None:
      with self._held_key_lock:
        self._held_key_vks[name] = vk
    self.key_pressed.emit(name)

  def _on_release(self, key) -> None:
    name = normalize_key(key)
    with self._held_key_lock:
      self._held_key_vks.pop(name, None)
    self.key_released.emit(name)

  def _ensure_stuck_key_timer(self, _key: str) -> None:
    if not self._stuck_key_timer.isActive():
      self._stuck_key_timer.start()

  def _release_stuck_keys(self) -> None:
    with self._held_key_lock:
      stuck = [name for name, vk in self._held_key_vks.items() if not _is_vk_physically_down(vk)]
      for name in stuck:
        del self._held_key_vks[name]
      if not self._held_key_vks:
        self._stuck_key_timer.stop()
    for name in stuck:
      self.key_released.emit(name)
