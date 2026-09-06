"""系統匣選單：切換使用情境預設、開關四項功能、開啟設定、結束程式。"""
from __future__ import annotations

from PySide6.QtGui import QAction, QActionGroup, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from app.config import AppConfig
from app.platform.resource_path import resource_path
from app.profiles import PROFILE_DAILY, PROFILE_TEACHING
from app.version import APP_NAME, APP_VERSION

_ICON_PATH = resource_path("assets", "tray_icon.png")


def _load_tray_icon() -> QIcon:
  if _ICON_PATH.exists():
    return QIcon(str(_ICON_PATH))
  return QApplication.instance().style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)


class TrayIcon(QSystemTrayIcon):
  def __init__(
    self,
    get_config,
    on_apply_profile,
    on_toggle_spotlight,
    on_toggle_click_effect,
    on_toggle_key_hud,
    on_toggle_find_cursor,
    on_open_settings,
    on_quit,
    parent=None,
  ):
    super().__init__(_load_tray_icon(), parent)
    self._get_config = get_config
    self._on_apply_profile = on_apply_profile
    self._on_toggle_spotlight = on_toggle_spotlight
    self._on_toggle_click_effect = on_toggle_click_effect
    self._on_toggle_key_hud = on_toggle_key_hud
    self._on_toggle_find_cursor = on_toggle_find_cursor
    self._on_open_settings = on_open_settings
    self._on_quit = on_quit
    self.setToolTip(f"{APP_NAME} v{APP_VERSION}")
    self._menu = QMenu()
    self._build_menu()
    self.setContextMenu(self._menu)
    self.setVisible(True)

  def _build_menu(self) -> None:
    profile_menu = self._menu.addMenu("使用情境")
    self._teaching_action = profile_menu.addAction("教學模式")
    self._teaching_action.setCheckable(True)
    self._teaching_action.triggered.connect(lambda: self._on_apply_profile(PROFILE_TEACHING))
    self._daily_action = profile_menu.addAction("日常模式")
    self._daily_action.setCheckable(True)
    self._daily_action.triggered.connect(lambda: self._on_apply_profile(PROFILE_DAILY))

    # 用 QActionGroup 讓兩個模式互斥，選單上會用勾選標示目前生效的是哪一個
    self._profile_action_group = QActionGroup(self._menu)
    self._profile_action_group.setExclusive(True)
    self._profile_action_group.addAction(self._teaching_action)
    self._profile_action_group.addAction(self._daily_action)

    self._menu.addSeparator()

    self._spotlight_action = self._add_checkable("游標高亮/聚光燈", self._on_toggle_spotlight)
    self._click_effect_action = self._add_checkable("點擊視覺特效", self._on_toggle_click_effect)
    self._key_hud_action = self._add_checkable("按鍵/按鈕顯示", self._on_toggle_key_hud)
    self._find_cursor_action = self._add_checkable("尋找游標輔助", self._on_toggle_find_cursor)

    self._menu.addSeparator()
    settings_action = self._menu.addAction("設定...")
    settings_action.triggered.connect(self._on_open_settings)

    self._menu.addSeparator()
    quit_action = self._menu.addAction("結束")
    quit_action.triggered.connect(self._on_quit)

  def _add_checkable(self, label: str, on_toggle) -> QAction:
    action = self._menu.addAction(label)
    action.setCheckable(True)
    action.toggled.connect(on_toggle)
    return action

  def sync_from_config(self, config: AppConfig) -> None:
    self._teaching_action.setChecked(config.active_profile == PROFILE_TEACHING)
    self._daily_action.setChecked(config.active_profile == PROFILE_DAILY)

    for action, enabled in (
      (self._spotlight_action, config.spotlight.enabled),
      (self._click_effect_action, config.click_effect.enabled),
      (self._key_hud_action, config.key_hud.enabled),
      (self._find_cursor_action, config.find_cursor.enabled),
    ):
      action.blockSignals(True)
      action.setChecked(enabled)
      action.blockSignals(False)
