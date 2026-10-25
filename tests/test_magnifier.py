"""測試放大鏡擷取範圍與鏡片位置的計算：擷取範圍以游標為中心、鏡片預設在游標右下方、靠邊時翻轉，
出現提示視窗時改用涵蓋提示的長方形範圍。"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRect

from app.magnifier.magnifier_window import (
  compute_lens_rect,
  compute_source_rect,
  compute_tooltip_view,
  lens_offset,
  regions_near_cursor,
)

_SCREEN = QRect(0, 0, 1920, 1080)


def test_source_rect_centered_on_cursor() -> None:
  rect = compute_source_rect(QPointF(960, 540), lens_size=240, zoom=2.0)
  assert rect == QRect(900, 480, 120, 120)


def test_source_rect_stays_centered_at_screen_corner() -> None:
  # 游標在角落時擷取範圍不夾回螢幕內，放大中心才會對準游標本身
  rect = compute_source_rect(QPointF(0, 0), lens_size=200, zoom=4.0)
  assert rect == QRect(-25, -25, 50, 50)


def test_lens_offset_larger_without_capture_exclusion() -> None:
  assert lens_offset(240, 2.0, excluded_from_capture=True) == 24
  assert lens_offset(240, 2.0, excluded_from_capture=False) == 60 + 16


def test_lens_rect_defaults_to_bottom_right_of_cursor() -> None:
  rect = compute_lens_rect(QPointF(960, 540), 240, 240, _SCREEN, offset=24)
  assert rect == QRect(984, 564, 240, 240)


def test_lens_rect_flips_left_near_right_edge() -> None:
  rect = compute_lens_rect(QPointF(1800, 300), 240, 240, _SCREEN, offset=24)
  assert rect == QRect(1536, 324, 240, 240)


def test_lens_rect_flips_up_near_bottom_edge() -> None:
  rect = compute_lens_rect(QPointF(300, 1000), 240, 240, _SCREEN, offset=24)
  assert rect == QRect(324, 736, 240, 240)


def test_lens_rect_flips_both_at_bottom_right_corner() -> None:
  rect = compute_lens_rect(QPointF(1919, 1079), 240, 240, _SCREEN, offset=24)
  assert rect == QRect(1655, 815, 240, 240)


def test_lens_rect_at_top_left_corner_stays_bottom_right() -> None:
  rect = compute_lens_rect(QPointF(0, 0), 240, 240, _SCREEN, offset=24)
  assert rect == QRect(24, 24, 240, 240)


def test_lens_rect_on_secondary_screen_with_offset_origin() -> None:
  screen = QRect(-1280, -200, 1280, 1024)
  rect = compute_lens_rect(QPointF(-100, -150), 200, 200, screen, offset=24)
  assert rect == QRect(-324, -126, 200, 200)


def test_lens_rect_clamped_when_screen_too_small_to_flip() -> None:
  small = QRect(0, 0, 300, 300)
  rect = compute_lens_rect(QPointF(150, 150), 240, 240, small, offset=24)
  assert small.contains(rect)


def test_lens_rect_without_capture_exclusion_does_not_overlap_source() -> None:
  cursor = QPointF(960, 540)
  offset = lens_offset(240, 2.0, excluded_from_capture=False)
  lens = compute_lens_rect(cursor, 240, 240, _SCREEN, offset)
  assert not lens.intersects(compute_source_rect(cursor, 240, 2.0))


def test_lens_rect_moves_above_when_tooltip_below_right() -> None:
  # 提示視窗通常出現在游標右下方，鏡片應改到右上方避開
  tooltip = QRect(970, 560, 200, 30)
  rect = compute_lens_rect(QPointF(960, 540), 240, 240, _SCREEN, offset=24, obstacles=[tooltip])
  assert rect == QRect(984, 276, 240, 240)
  assert not rect.intersects(tooltip)


def test_lens_rect_moves_left_when_tooltip_blocks_right_side() -> None:
  tooltip = QRect(970, 200, 400, 700)
  rect = compute_lens_rect(QPointF(960, 540), 240, 240, _SCREEN, offset=24, obstacles=[tooltip])
  assert rect == QRect(696, 564, 240, 240)


def test_lens_rect_picks_least_overlap_when_all_positions_blocked() -> None:
  blocker = QRect(0, 0, 1920, 1080)
  small_tooltip = QRect(984, 564, 50, 50)
  rect = compute_lens_rect(QPointF(960, 540), 240, 240, _SCREEN, offset=24, obstacles=[blocker, small_tooltip])
  assert not rect.intersects(small_tooltip)


def test_lens_rect_supports_rectangular_size() -> None:
  rect = compute_lens_rect(QPointF(960, 540), 500, 120, _SCREEN, offset=24)
  assert rect == QRect(984, 564, 500, 120)


def test_regions_near_cursor_ignores_far_tooltips() -> None:
  near = QRect(964, 560, 120, 24)
  far = QRect(300, 100, 120, 24)
  assert regions_near_cursor(QPointF(960, 540), [near, far], max_distance=120) == [near]


def test_tooltip_view_covers_cursor_area_and_tooltip_at_full_zoom() -> None:
  cursor = QPointF(700, 400)
  tooltip = QRect(706, 439, 205, 20)
  source, scale = compute_tooltip_view(cursor, 240, 2.0, [tooltip], _SCREEN)
  assert scale == 2.0
  assert source.contains(tooltip)
  assert source.contains(compute_source_rect(cursor, 240, 2.0))
  assert source.width() != source.height()  # 長方形，依涵蓋內容的比例


def test_tooltip_view_reduces_zoom_to_fit_screen_ratio() -> None:
  # 涵蓋範圍放大後超過螢幕寬度 60% 時降低倍率
  tooltip = QRect(706, 439, 800, 20)
  source, scale = compute_tooltip_view(QPointF(700, 400), 240, 4.0, [tooltip], _SCREEN)
  assert 1.0 <= scale < 4.0
  assert source.width() * scale <= 1920 * 0.6 + 1


def test_tooltip_view_falls_back_to_tooltip_only_when_cursor_area_too_large() -> None:
  # 游標周圍加提示在 1 倍下仍超出上限時，只涵蓋提示本身
  cursor = QPointF(100, 100)
  tooltip = QRect(104, 120, 1100, 20)
  source, scale = compute_tooltip_view(cursor, 600, 1.5, [tooltip], _SCREEN)
  assert scale >= 1.0
  assert source.contains(tooltip)
  assert not source.contains(compute_source_rect(cursor, 600, 1.5))


def test_tooltip_view_crops_around_tooltip_when_even_tooltip_too_large() -> None:
  tooltip = QRect(0, 100, 1900, 20)
  source, scale = compute_tooltip_view(QPointF(10, 90), 240, 2.0, [tooltip], _SCREEN)
  assert scale == 1.0
  assert source.width() <= 1920 * 0.6
  assert abs(source.center().x() - tooltip.center().x()) <= 1
