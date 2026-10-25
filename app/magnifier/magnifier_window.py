"""跟隨游標的放大鏡鏡片：持續擷取游標周圍的畫面並放大顯示。"""
from __future__ import annotations

import math
import sys
import time
from typing import Sequence

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QColor, QCursor, QFont, QImage, QPainter, QPainterPath, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from app.config import MagnifierConfig
from app.overlay import base_overlay_widget
from app.platform.screen_utils import screen_containing_point
from app.platform.win_capture_exclusion import exclude_from_capture

_REFRESH_INTERVAL_MS = 16
_BORDER_WIDTH = 3
_CROSSHAIR_HALF_LENGTH = 8
_CURSOR_OFFSET = 24  # 鏡片與游標的間距，留出游標箭頭本身的空間
_FALLBACK_MARGIN = 16
_COVER_MARGIN = 8  # 涵蓋提示視窗時四周多留的邊距，避免提示貼齊鏡片邊緣
_STATUS_DURATION_S = 1.5
_TOOLTIP_MAX_DISTANCE = 120  # 提示視窗距游標多遠以內才視為「目前這個提示」，邏輯像素
# 涵蓋提示時長方形鏡片最大可佔螢幕的比例，超過就降低倍率
_TOOLTIP_LENS_MAX_WIDTH_RATIO = 0.6
_TOOLTIP_LENS_MAX_HEIGHT_RATIO = 0.5


def compute_source_rect(cursor: QPointF, lens_size: int, zoom: float) -> QRect:
  """以游標為中心、邊長 lens_size / zoom 的擷取範圍；不夾回螢幕內，讓游標在角落時放大中心仍對準游標。"""
  side = max(1, round(lens_size / zoom))
  return QRect(round(cursor.x() - side / 2), round(cursor.y() - side / 2), side, side)


def regions_near_cursor(cursor: QPointF, regions: Sequence[QRect], max_distance: float) -> list[QRect]:
  """只保留距離游標 max_distance 內的區域；游標移走後提示通常還會停留一下，不應把放大範圍拉過去。"""
  near = []
  for region in regions:
    dx = max(region.left() - cursor.x(), 0, cursor.x() - (region.left() + region.width()))
    dy = max(region.top() - cursor.y(), 0, cursor.y() - (region.top() + region.height()))
    if math.hypot(dx, dy) <= max_distance:
      near.append(region)
  return near


def _united(rects: Sequence[QRect]) -> QRect:
  result = QRect(rects[0])
  for rect in rects[1:]:
    result = result.united(rect)
  return result


def _fit_scale(source: QRect, zoom: float, max_width: float, max_height: float) -> float:
  return min(zoom, max_width / source.width(), max_height / source.height())


def compute_tooltip_view(
  cursor: QPointF, lens_size: int, zoom: float, regions: Sequence[QRect], screen_rect: QRect
) -> tuple[QRect, float]:
  """出現提示視窗時的長方形擷取範圍與實際倍率，回傳 (擷取範圍, 倍率)。

  擷取範圍同時涵蓋游標周圍與提示；放大後的長方形鏡片超出螢幕比例上限時降低倍率，
  降到 1 倍仍放不下就只涵蓋提示本身，再放不下則以提示為中心裁切。
  """
  max_width = screen_rect.width() * _TOOLTIP_LENS_MAX_WIDTH_RATIO
  max_height = screen_rect.height() * _TOOLTIP_LENS_MAX_HEIGHT_RATIO
  margin = _COVER_MARGIN

  covered = _united([compute_source_rect(cursor, lens_size, zoom), *regions]).adjusted(-margin, -margin, margin, margin)
  scale = _fit_scale(covered, zoom, max_width, max_height)
  if scale >= 1.0:
    return covered, scale

  tooltip_only = _united(list(regions)).adjusted(-margin, -margin, margin, margin)
  scale = _fit_scale(tooltip_only, zoom, max_width, max_height)
  if scale >= 1.0:
    return tooltip_only, scale

  width = min(tooltip_only.width(), math.floor(max_width))
  height = min(tooltip_only.height(), math.floor(max_height))
  center_x = tooltip_only.left() + tooltip_only.width() / 2
  center_y = tooltip_only.top() + tooltip_only.height() / 2
  return QRect(round(center_x - width / 2), round(center_y - height / 2), width, height), 1.0


def _clamp_into(rect: QRect, bounds: QRect) -> QRect:
  left = min(max(rect.left(), bounds.left()), bounds.left() + bounds.width() - rect.width())
  top = min(max(rect.top(), bounds.top()), bounds.top() + bounds.height() - rect.height())
  return QRect(left, top, rect.width(), rect.height())


def _overlap_area(rect: QRect, obstacles: Sequence[QRect]) -> int:
  total = 0
  for obstacle in obstacles:
    overlap = rect.intersected(obstacle)
    if not overlap.isEmpty():
      total += overlap.width() * overlap.height()
  return total


def lens_offset(lens_size: int, zoom: float, excluded_from_capture: bool) -> int:
  """鏡片與游標的間距；無法把鏡片排除於截圖之外時加大，避免鏡片落在擷取範圍內截到自己。"""
  if excluded_from_capture:
    return _CURSOR_OFFSET
  return max(_CURSOR_OFFSET, math.ceil(lens_size / zoom / 2) + _FALLBACK_MARGIN)


def compute_lens_rect(
  cursor: QPointF,
  width: int,
  height: int,
  screen_rect: QRect,
  offset: int,
  obstacles: Sequence[QRect] = (),
) -> QRect:
  """依右下、右上、左下、左上的順序，挑第一個完整在螢幕內且不蓋到障礙物（如提示視窗）的位置。

  每個位置都蓋到障礙物時取重疊面積最小者；螢幕小到四個位置都放不下時，夾回螢幕內。
  """
  x, y = round(cursor.x()), round(cursor.y())
  right_left, left_left = x + offset, x - offset - width
  below_top, above_top = y + offset, y - offset - height
  candidates = [
    QRect(left, top, width, height)
    for left, top in (
      (right_left, below_top),
      (right_left, above_top),
      (left_left, below_top),
      (left_left, above_top),
    )
  ]

  fitting = [rect for rect in candidates if screen_rect.contains(rect)]
  if not fitting:
    return _clamp_into(candidates[0], screen_rect)
  return min(fitting, key=lambda rect: _overlap_area(rect, obstacles))


def logical_to_physical_rect(rect: QRect, dpr: float) -> tuple[int, int, int, int]:
  """與 screen_utils.physical_to_logical_point 的換算方式互為反向（實體 = 邏輯 × devicePixelRatio）。"""
  return (round(rect.left() * dpr), round(rect.top() * dpr), round(rect.width() * dpr), round(rect.height() * dpr))


class MagnifierWindow(QWidget):
  def __init__(self, config: MagnifierConfig, parent: QWidget | None = None):
    super().__init__(parent)
    self._config = config
    self._cursor: QPointF | None = None
    self._frame: QImage | None = None
    self._frame_source: QRect | None = None
    self._frame_captured: QRect | None = None
    self._frame_cursor: QPointF | None = None
    self._tooltip_mode = False
    self._status_text = ""
    self._status_until = 0.0
    base_overlay_widget.apply_overlay_window_flags(self, click_through=True)
    self._excluded_from_capture = exclude_from_capture(int(self.winId()))
    self._capture_worker = self._create_capture_worker()
    self._tooltip_watcher = self._create_tooltip_watcher()
    self._timer = QTimer(self)
    self._timer.setInterval(_REFRESH_INTERVAL_MS)
    self._timer.timeout.connect(self._refresh)
    self.set_config(config)

  def _create_capture_worker(self):
    # QScreen.grabWindow 在 Windows 每次會被畫面合成卡住約一個 frame，放在主執行緒會拖慢整個程式，
    # 因此 Windows 改由背景執行緒擷取；其他平台仍用 grabWindow
    if sys.platform != "win32":
      return None
    from app.magnifier.capture_worker import CaptureWorker

    worker = CaptureWorker(self)
    worker.frame_ready.connect(self._on_frame_ready)
    return worker

  def _create_tooltip_watcher(self):
    # 提示視窗在游標離開圖示時就會消失，使用者無法移過去閱讀，因此鏡片要主動避開不蓋住它
    if sys.platform != "win32":
      return None
    from app.platform.win_tooltip_watcher import WinTooltipWatcher

    return WinTooltipWatcher()

  def set_config(self, config: MagnifierConfig) -> None:
    self._config = config
    if not config.enabled:
      self._stop()
      return
    if self.isHidden():
      # 用熱鍵開啟時滑鼠可能還沒移動過，先以目前游標位置定位，避免鏡片出現在舊位置
      cursor_pos = QCursor.pos()
      self._cursor = QPointF(cursor_pos.x(), cursor_pos.y())
      self._frame = None
    self._refresh()
    self.show()
    self._timer.start()
    if self._capture_worker is not None:
      self._capture_worker.start()
    if self._tooltip_watcher is not None:
      self._tooltip_watcher.start()

  def on_cursor_moved(self, x: int, y: int) -> None:
    # 只記錄位置，移動與擷取統一交給計時器；高回報率滑鼠每秒上千筆事件，逐筆處理會塞爆主執行緒造成延遲
    self._cursor = QPointF(x, y)

  def show_status(self, text: str) -> None:
    """在鏡片上短暫顯示狀態文字（如切換「放大提示」時的回饋）。"""
    self._status_text = text
    self._status_until = time.monotonic() + _STATUS_DURATION_S
    self.update()

  def closeEvent(self, event: QCloseEvent) -> None:
    self._stop()
    super().closeEvent(event)

  def _stop(self) -> None:
    self._timer.stop()
    if self._capture_worker is not None:
      self._capture_worker.stop()
    if self._tooltip_watcher is not None:
      self._tooltip_watcher.stop()
    self.hide()

  def _refresh(self) -> None:
    if self._cursor is None:
      return
    screen = screen_containing_point(round(self._cursor.x()), round(self._cursor.y()))
    if screen is None:
      return
    screen_rect = screen.geometry()
    lens_size = self._config.lens_size
    zoom = self._config.zoom_factor

    tooltips = self._tooltip_watcher.tooltip_rects() if self._tooltip_watcher is not None else []
    obstacles = regions_near_cursor(self._cursor, tooltips, _TOOLTIP_MAX_DISTANCE)
    # 無法排除於截圖之外時不擴大範圍，否則擴大後的擷取範圍可能涵蓋到鏡片本身
    self._tooltip_mode = bool(obstacles) and self._config.include_tooltip and self._excluded_from_capture
    if self._tooltip_mode:
      source, scale = compute_tooltip_view(self._cursor, lens_size, zoom, obstacles, screen_rect)
      lens_width, lens_height = round(source.width() * scale), round(source.height() * scale)
    else:
      source = compute_source_rect(self._cursor, lens_size, zoom)
      lens_width = lens_height = lens_size

    offset = lens_offset(lens_size, zoom, self._excluded_from_capture)
    lens_rect = compute_lens_rect(self._cursor, lens_width, lens_height, screen_rect, offset, obstacles)
    if lens_rect != self.geometry():
      self.setGeometry(lens_rect)

    captured = source.intersected(screen_rect)
    if self._capture_worker is not None:
      self._capture_worker.set_request(
        source, captured, logical_to_physical_rect(captured, screen.devicePixelRatio()), self._cursor
      )
      return

    image = None
    if not captured.isEmpty():
      # grabWindow(0, ...) 的座標是相對於該螢幕左上角
      image = screen.grabWindow(
        0,
        captured.left() - screen_rect.left(),
        captured.top() - screen_rect.top(),
        captured.width(),
        captured.height(),
      ).toImage()
    self._on_frame_ready(image, source, captured, QPointF(self._cursor))

  def _on_frame_ready(self, image: QImage | None, source: QRect, captured: QRect, cursor: QPointF) -> None:
    self._frame = image
    self._frame_cursor = cursor
    self._frame_source = source
    self._frame_captured = captured
    self.update()

  def paintEvent(self, event: QPaintEvent) -> None:
    if self._frame_source is None:
      return
    painter = QPainter(self)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    inset = _BORDER_WIDTH / 2
    lens_rect = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
    lens_path = QPainterPath()
    # 涵蓋提示時固定用長方形，圓形會把提示文字的左右兩端裁掉
    if self._tooltip_mode or self._config.shape == "square":
      lens_path.addRect(lens_rect)
    else:
      lens_path.addEllipse(lens_rect)

    painter.setClipPath(lens_path)
    # 擷取範圍超出螢幕的部分沒有畫面，以黑色填滿
    painter.fillRect(self.rect(), QColor(0, 0, 0))
    if self._frame is not None and not self._frame.isNull():
      painter.drawImage(self._map_to_lens(self._frame_captured), self._frame, QRectF(self._frame.rect()))
    self._paint_crosshair(painter)
    painter.setClipping(False)

    painter.setPen(QPen(QColor(self._config.border_color), _BORDER_WIDTH))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(lens_path)
    self._paint_status(painter)

  def _lens_scale(self) -> tuple[float, float]:
    # 分開計算水平與垂直比例：切換一般/提示模式的瞬間，鏡片尺寸可能已更新但畫面還是上一幀
    return self.width() / self._frame_source.width(), self.height() / self._frame_source.height()

  def _map_to_lens(self, global_rect: QRect) -> QRectF:
    scale_x, scale_y = self._lens_scale()
    return QRectF(
      (global_rect.left() - self._frame_source.left()) * scale_x,
      (global_rect.top() - self._frame_source.top()) * scale_y,
      global_rect.width() * scale_x,
      global_rect.height() * scale_y,
    )

  def _paint_status(self, painter: QPainter) -> None:
    if not self._status_text:
      return
    if time.monotonic() > self._status_until:
      self._status_text = ""
      return
    font = QFont()
    font.setPixelSize(16)
    font.setBold(True)
    painter.setFont(font)
    # 長方形模式下提示多半在鏡片下半部，狀態文字改放上方避免擋住
    text_top = 12 if self._tooltip_mode else self.height() * 0.62
    text_rect = QRectF(0, text_top, self.width(), 30)
    background = painter.fontMetrics().boundingRect(self._status_text).adjusted(-10, -5, 10, 5)
    background.moveCenter(text_rect.center().toPoint())
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 190))
    painter.drawRoundedRect(QRectF(background), 6, 6)
    painter.setPen(QColor(255, 255, 255))
    painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self._status_text)

  def _paint_crosshair(self, painter: QPainter) -> None:
    # 擷取畫面不含系統游標，用小十字標出游標在鏡片中對應的位置；
    # 一般情況擷取範圍以游標為中心，涵蓋提示視窗時則會偏離中央
    if self._frame_cursor is None:
      return
    scale_x, scale_y = self._lens_scale()
    center = QPointF(
      (self._frame_cursor.x() - self._frame_source.left()) * scale_x,
      (self._frame_cursor.y() - self._frame_source.top()) * scale_y,
    )
    painter.setPen(QPen(QColor(255, 0, 0, 200), 1.5))
    painter.drawLine(
      QPointF(center.x() - _CROSSHAIR_HALF_LENGTH, center.y()),
      QPointF(center.x() + _CROSSHAIR_HALF_LENGTH, center.y()),
    )
    painter.drawLine(
      QPointF(center.x(), center.y() - _CROSSHAIR_HALF_LENGTH),
      QPointF(center.x(), center.y() + _CROSSHAIR_HALF_LENGTH),
    )
