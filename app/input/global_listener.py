"""包裝 pynput 的全域滑鼠/鍵盤監聽，透過 Qt signal 安全送回主執行緒。"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from pynput import keyboard, mouse

from app.input.events import normalize_key
from app.platform.screen_utils import capture_screen_dpi_info, physical_to_logical_point

_BUTTON_NAMES = {
  mouse.Button.left: "left",
  mouse.Button.right: "right",
  mouse.Button.middle: "middle",
}


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
    name = _BUTTON_NAMES.get(button, str(button))
    if pressed:
      self.mouse_pressed.emit(logical_x, logical_y, name)
    else:
      self.mouse_released.emit(logical_x, logical_y, name)

  def _on_press(self, key) -> None:
    self.key_pressed.emit(normalize_key(key))

  def _on_release(self, key) -> None:
    self.key_released.emit(normalize_key(key))
