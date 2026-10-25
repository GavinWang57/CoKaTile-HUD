"""在背景執行緒持續擷取放大鏡所需的螢幕區域，避免截圖的等待時間卡住主執行緒。"""
from __future__ import annotations

import threading
import time

from PySide6.QtCore import QObject, QPointF, QRect, Signal
from PySide6.QtGui import QImage

from app.platform.win_screen_capture import GdiRegionCapturer

_FRAME_INTERVAL_S = 1 / 60


class CaptureWorker(QObject):
  # (畫面, 擷取當下的放大來源範圍, 實際擷取到的範圍, 當時的游標位置)，皆為邏輯座標
  frame_ready = Signal(QImage, QRect, QRect, QPointF)

  def __init__(self, parent: QObject | None = None):
    super().__init__(parent)
    self._lock = threading.Lock()
    self._request: tuple[QRect, QRect, tuple[int, int, int, int], QPointF] | None = None
    self._running = threading.Event()
    self._thread: threading.Thread | None = None

  def set_request(
    self, source: QRect, captured: QRect, physical: tuple[int, int, int, int], cursor: QPointF
  ) -> None:
    with self._lock:
      self._request = (QRect(source), QRect(captured), physical, QPointF(cursor))

  def start(self) -> None:
    if self._thread is not None:
      return
    self._running.set()
    self._thread = threading.Thread(target=self._run, name="MagnifierCapture", daemon=True)
    self._thread.start()

  def stop(self) -> None:
    if self._thread is None:
      return
    self._running.clear()
    self._thread.join(timeout=1.0)
    self._thread = None

  def _run(self) -> None:
    capturer = GdiRegionCapturer()
    try:
      while self._running.is_set():
        started = time.perf_counter()
        with self._lock:
          request = self._request
        if request is not None:
          source, captured, (x, y, width, height), cursor = request
          if width > 0 and height > 0:
            self.frame_ready.emit(capturer.capture(x, y, width, height), source, captured, cursor)
        # BitBlt 本身通常會等到下一次畫面合成，這裡只在擷取很快時補足間隔，避免空轉吃滿 CPU
        remaining = _FRAME_INTERVAL_S - (time.perf_counter() - started)
        if remaining > 0:
          time.sleep(remaining)
    finally:
      capturer.close()
