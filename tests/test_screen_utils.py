"""測試實體像素座標換算成 Qt 邏輯座標的邏輯，涵蓋 Windows 顯示縮放（如 125%）情境。"""
from __future__ import annotations

import pytest

from app.platform.screen_utils import physical_to_logical_point

# 單一螢幕、125% 縮放，邏輯解析度 2048x1152（對應實體 2560x1440）
_SINGLE_SCREEN_125 = [(0, 0, 2047, 1151, 1.25)]


def test_origin_has_no_offset() -> None:
  assert physical_to_logical_point(0, 0, _SINGLE_SCREEN_125) == (0, 0)


def test_scales_down_by_device_pixel_ratio() -> None:
  # 對應實測情境：實體 (918, 885) 應換算回邏輯 (734, 708) 附近
  x, y = physical_to_logical_point(918, 885, _SINGLE_SCREEN_125)
  assert x == pytest.approx(734, abs=1)
  assert y == pytest.approx(708, abs=1)


def test_scales_correctly_regardless_of_distance_from_origin() -> None:
  # 換算前（未修正時）座標離原點越遠、物理/邏輯座標的誤差越大，這裡驗證換算後兩點都精準對應
  near_origin_x, _ = physical_to_logical_point(100, 100, _SINGLE_SCREEN_125)
  far_x, _ = physical_to_logical_point(2000, 100, _SINGLE_SCREEN_125)
  assert near_origin_x == pytest.approx(80, abs=1)
  assert far_x == pytest.approx(1600, abs=1)


def test_picks_correct_screen_in_multi_monitor_setup() -> None:
  # 左邊螢幕 100%、右邊螢幕接續在後且為 125%
  screens = [(0, 0, 1919, 1079, 1.0), (1920, 0, 3967, 1151, 1.25)]

  left_result = physical_to_logical_point(500, 500, screens)
  right_result = physical_to_logical_point(2500, 500, screens)

  assert left_result == (500, 500)
  assert right_result[0] > 1920  # 應落在右邊螢幕的邏輯範圍內


def test_falls_back_to_first_screen_when_no_match() -> None:
  # 遊標座標剛好落在螢幕邊界外一點點時，退回第一個螢幕的縮放比例，不應拋例外
  x, y = physical_to_logical_point(-5, -5, _SINGLE_SCREEN_125)
  assert isinstance(x, int)
  assert isinstance(y, int)


def test_no_screen_info_returns_input_unchanged() -> None:
  assert physical_to_logical_point(123, 456, []) == (123, 456)
