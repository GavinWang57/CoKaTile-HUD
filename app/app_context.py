"""組裝所有模組並串接 signal/slot 的 composition root。"""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QObject, QPointF
from PySide6.QtGui import QGuiApplication

from app.config import AppConfig, ConfigManager
from app.hud.key_hud_window import KeyHudWindow
from app.input.events import display_label
from app.input.global_listener import GlobalInputListener
from app.input.hotkey_manager import HotkeyManager
from app.input.shake_detector import ShakeDetector
from app.overlay.overlay_manager import OverlayManager
from app.platform import permissions_macos
from app.platform.screen_utils import screen_containing_point
from app.profiles import apply_profile
from app.settings_ui.settings_dialog import SettingsDialog
from app.tray.tray_icon import TrayIcon


class AppContext(QObject):
  def __init__(self, parent: QObject | None = None):
    super().__init__(parent)
    self._config_manager = ConfigManager()
    self._config: AppConfig = self._config_manager.load()

    self._listener = GlobalInputListener(self)
    self._overlay_manager = OverlayManager(self._config, self)
    self._hud_windows: dict = {}
    self._shake_detector = ShakeDetector(parent=self)
    self._hotkey_manager = HotkeyManager(self._config.find_cursor.trigger_hotkey, self)
    self._settings_dialog: SettingsDialog | None = None

    self._build_hud_windows()
    self._connect_signals()
    self._apply_config_to_components()

    if permissions_macos.is_macos() and permissions_macos.has_accessibility_permission() is False:
      permissions_macos.prompt_accessibility_permission()

    self._tray = TrayIcon(
      get_config=lambda: self._config,
      on_apply_profile=self._on_apply_profile,
      on_toggle_spotlight=self._on_toggle_spotlight,
      on_toggle_click_effect=self._on_toggle_click_effect,
      on_toggle_key_hud=self._on_toggle_key_hud,
      on_toggle_find_cursor=self._on_toggle_find_cursor,
      on_open_settings=self._open_settings,
      on_quit=self._quit,
    )
    self._tray.sync_from_config(self._config)

    self._listener.start()

  def _build_hud_windows(self) -> None:
    app = QGuiApplication.instance()
    for screen in app.screens():
      self._hud_windows[screen] = KeyHudWindow(screen.geometry(), self._config.key_hud)
    app.screenAdded.connect(self._on_screen_added)
    app.screenRemoved.connect(self._on_screen_removed)

  def _on_screen_added(self, screen) -> None:
    self._hud_windows[screen] = KeyHudWindow(screen.geometry(), self._config.key_hud)
    self._sync_hud_visibility()
    self._listener.refresh_screen_dpi_info()

  def _on_screen_removed(self, screen) -> None:
    window = self._hud_windows.pop(screen, None)
    if window is not None:
      window.close()
    self._listener.refresh_screen_dpi_info()

  def _connect_signals(self) -> None:
    self._listener.mouse_moved.connect(self._overlay_manager.on_cursor_moved)
    self._listener.mouse_moved.connect(self._shake_detector.on_mouse_moved)
    self._listener.mouse_moved.connect(self._on_mouse_moved_for_hud_anchor)
    self._listener.mouse_pressed.connect(self._overlay_manager.on_mouse_pressed)
    self._listener.mouse_pressed.connect(self._on_mouse_pressed_for_hud)
    self._listener.mouse_released.connect(self._on_mouse_released_for_hud)
    self._listener.key_pressed.connect(self._on_key_pressed)
    self._listener.key_pressed.connect(self._hotkey_manager.on_key_pressed)
    self._listener.key_released.connect(self._on_key_released_for_hud)
    self._listener.key_released.connect(self._hotkey_manager.on_key_released)
    self._listener.listener_error.connect(self._on_listener_error)

    self._shake_detector.shake_detected.connect(self._overlay_manager.trigger_find_cursor)
    self._hotkey_manager.hotkey_triggered.connect(self._overlay_manager.trigger_find_cursor)

  def _on_mouse_moved_for_hud_anchor(self, x: int, y: int) -> None:
    if self._config.key_hud.enabled and self._config.key_hud.corner == "follow_cursor":
      self._active_hud_window().set_cursor_anchor(QPointF(x, y))

  def _on_key_pressed(self, key: str) -> None:
    if self._config.key_hud.enabled:
      self._active_hud_window().on_key_event_pressed(key_id=f"kb:{key}", display_text=display_label(key))

  def _on_key_released_for_hud(self, key: str) -> None:
    if not self._config.key_hud.enabled:
      return
    key_id = f"kb:{key}"
    # 廣播給所有螢幕的 HUD 視窗，避免按下與放開之間游標剛好換了螢幕導致徽章卡在「按住」狀態
    for window in self._hud_windows.values():
      window.on_key_event_released(key_id)

  def _on_mouse_pressed_for_hud(self, x: int, y: int, button: str) -> None:
    if self._config.key_hud.enabled and self._config.key_hud.show_mouse_buttons:
      label = {"left": "左鍵", "right": "右鍵", "middle": "中鍵"}.get(button, button)
      self._active_hud_window().on_key_event_pressed(key_id=f"mouse:{button}", display_text=label)

  def _on_mouse_released_for_hud(self, x: int, y: int, button: str) -> None:
    if not (self._config.key_hud.enabled and self._config.key_hud.show_mouse_buttons):
      return
    key_id = f"mouse:{button}"
    for window in self._hud_windows.values():
      window.on_key_event_released(key_id)

  def _active_hud_window(self) -> KeyHudWindow:
    screens = QGuiApplication.instance().screens()
    if 0 <= self._config.key_hud.screen_index < len(screens):
      return self._hud_windows[screens[self._config.key_hud.screen_index]]
    cursor_pos = self._overlay_manager.cursor_global_pos
    if cursor_pos is not None:
      screen = screen_containing_point(int(cursor_pos.x()), int(cursor_pos.y()))
      if screen in self._hud_windows:
        return self._hud_windows[screen]
    return next(iter(self._hud_windows.values()))

  def _on_listener_error(self, message: str) -> None:
    print(f"[GlobalInputListener] 監聽啟動失敗: {message}")

  def _on_apply_profile(self, profile: str) -> None:
    self._config = apply_profile(self._config, profile)
    self._save_and_apply()
    self._tray.sync_from_config(self._config)

  def _on_toggle_spotlight(self, enabled: bool) -> None:
    self._config = replace(self._config, spotlight=replace(self._config.spotlight, enabled=enabled))
    self._save_and_apply()

  def _on_toggle_click_effect(self, enabled: bool) -> None:
    self._config = replace(
      self._config, click_effect=replace(self._config.click_effect, enabled=enabled)
    )
    self._save_and_apply()

  def _on_toggle_key_hud(self, enabled: bool) -> None:
    self._config = replace(self._config, key_hud=replace(self._config.key_hud, enabled=enabled))
    self._save_and_apply()

  def _on_toggle_find_cursor(self, enabled: bool) -> None:
    self._config = replace(
      self._config, find_cursor=replace(self._config.find_cursor, enabled=enabled)
    )
    self._save_and_apply()

  def _save_and_apply(self) -> None:
    self._config_manager.save(self._config)
    self._apply_config_to_components()

  def _apply_config_to_components(self) -> None:
    self._overlay_manager.set_config(self._config)
    for window in self._hud_windows.values():
      window.set_config(self._config.key_hud)
    self._sync_hud_visibility()
    self._hotkey_manager.set_combo(self._config.find_cursor.trigger_hotkey)

  def _sync_hud_visibility(self) -> None:
    for window in self._hud_windows.values():
      window.setVisible(self._config.key_hud.enabled)

  def _open_settings(self) -> None:
    if self._settings_dialog is not None:
      self._settings_dialog.close()
    self._settings_dialog = SettingsDialog(self._config, self._on_settings_applied)
    self._settings_dialog.show()

  def _on_settings_applied(self, new_config: AppConfig) -> None:
    self._config = new_config
    self._save_and_apply()
    self._tray.sync_from_config(self._config)

  def _quit(self) -> None:
    self._listener.stop()
    self._overlay_manager.shutdown()
    for window in self._hud_windows.values():
      window.close()
    QGuiApplication.instance().quit()
