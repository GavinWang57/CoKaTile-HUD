"""產生系統匣用的簡易滑鼠圖示。僅需執行一次，或圖示設計異動時重新執行：

    python scripts/generate_tray_icon.py
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPainterPath, QPen, QPixmap

_SIZE = 256
_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "assets" / "tray_icon.png"
_LINE_COLOR = "#3A3A3A"
_BODY_COLOR = "#F4F4F4"


def _draw_mouse_icon() -> QPixmap:
  pixmap = QPixmap(_SIZE, _SIZE)
  pixmap.fill(Qt.GlobalColor.transparent)

  painter = QPainter(pixmap)
  painter.setRenderHint(QPainter.RenderHint.Antialiasing)

  margin_x = _SIZE * 0.22
  body_rect = QRectF(margin_x, _SIZE * 0.08, _SIZE - margin_x * 2, _SIZE * 0.84)

  body_path = QPainterPath()
  body_path.addRoundedRect(body_rect, body_rect.width() * 0.5, body_rect.width() * 0.5)

  painter.setPen(QPen(QColor(_LINE_COLOR), _SIZE * 0.045))
  painter.setBrush(QColor(_BODY_COLOR))
  painter.drawPath(body_path)

  # 左右鍵分隔線（只畫在滾輪上方一小段，避免與滾輪連成一塊）
  divider_top = QPointF(_SIZE / 2, body_rect.top() + body_rect.height() * 0.03)
  divider_bottom = QPointF(_SIZE / 2, body_rect.top() + body_rect.height() * 0.09)
  painter.setPen(QPen(QColor(_LINE_COLOR), _SIZE * 0.035))
  painter.drawLine(divider_top, divider_bottom)

  # 滾輪
  wheel_width = _SIZE * 0.09
  wheel_rect = QRectF(
    _SIZE / 2 - wheel_width / 2,
    body_rect.top() + body_rect.height() * 0.14,
    wheel_width,
    _SIZE * 0.16,
  )
  painter.setPen(Qt.PenStyle.NoPen)
  painter.setBrush(QColor(_LINE_COLOR))
  painter.drawRoundedRect(wheel_rect, wheel_width / 2, wheel_width / 2)

  painter.end()
  return pixmap


def main() -> None:
  QGuiApplication([])
  pixmap = _draw_mouse_icon()
  _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
  pixmap.save(str(_OUTPUT_PATH), "PNG")
  print(f"已產生圖示：{_OUTPUT_PATH}")


if __name__ == "__main__":
  main()
