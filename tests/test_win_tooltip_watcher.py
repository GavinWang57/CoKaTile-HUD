"""測試提示視窗的判斷規則：類別名稱直接認定，其餘以游標附近的小型置頂浮動視窗推測。"""
from __future__ import annotations

from app.platform.win_tooltip_watcher import is_tooltip_like

_WS_POPUP = 0x80000000
_WS_CHILD = 0x40000000
_WS_EX_TOPMOST = 0x00000008
_WS_EX_TOOLWINDOW = 0x00000080
_CURSOR = (500, 500)


def test_tooltip_class_name_is_always_tooltip() -> None:
  assert is_tooltip_like("tooltips_class32", 0, 0, (0, 0, 10, 10), (3000, 3000))
  assert is_tooltip_like("Qt6110QWindowToolTipSaveBits", 0, 0, (0, 0, 10, 10), (3000, 3000))


def test_small_topmost_popup_near_cursor_is_tooltip() -> None:
  assert is_tooltip_like("Chrome_WidgetWin_1", _WS_POPUP, _WS_EX_TOPMOST, (510, 530, 700, 560), _CURSOR)


def test_popup_far_from_cursor_is_not_tooltip() -> None:
  assert not is_tooltip_like("Chrome_WidgetWin_1", _WS_POPUP, _WS_EX_TOOLWINDOW, (1500, 1500, 1700, 1530), _CURSOR)


def test_large_popup_is_not_tooltip() -> None:
  assert not is_tooltip_like("Chrome_WidgetWin_1", _WS_POPUP, _WS_EX_TOPMOST, (400, 400, 2000, 1400), _CURSOR)


def test_non_popup_or_child_window_is_not_tooltip() -> None:
  assert not is_tooltip_like("SomeWindow", 0, _WS_EX_TOPMOST, (510, 530, 700, 560), _CURSOR)
  assert not is_tooltip_like("SomeWindow", _WS_POPUP | _WS_CHILD, _WS_EX_TOPMOST, (510, 530, 700, 560), _CURSOR)


def test_popup_without_floating_ex_style_is_not_tooltip() -> None:
  assert not is_tooltip_like("SomeWindow", _WS_POPUP, 0, (510, 530, 700, 560), _CURSOR)
