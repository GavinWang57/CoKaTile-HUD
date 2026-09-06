"""調整聚光燈、點擊特效、按鍵 HUD、尋找游標等參數的設定視窗。"""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
  QCheckBox,
  QColorDialog,
  QComboBox,
  QDialog,
  QDoubleSpinBox,
  QFormLayout,
  QLineEdit,
  QPushButton,
  QSpinBox,
  QTabWidget,
  QVBoxLayout,
  QWidget,
)

from app.config import AppConfig

_HUD_POSITIONS = [
  ("top-left", "左上"),
  ("top-center", "中上"),
  ("top-right", "右上"),
  ("middle-left", "左中"),
  ("center", "中中"),
  ("middle-right", "右中"),
  ("bottom-left", "左下"),
  ("bottom-center", "中下"),
  ("bottom-right", "右下"),
  ("follow_cursor", "跟隨游標動態移動"),
]


class SettingsDialog(QDialog):
  def __init__(self, config: AppConfig, on_apply, parent=None):
    super().__init__(parent)
    self.setWindowTitle("設定")
    self._config = config
    self._on_apply = on_apply

    tabs = QTabWidget()
    tabs.addTab(self._build_spotlight_tab(), "游標高亮")
    tabs.addTab(self._build_click_effect_tab(), "點擊特效")
    tabs.addTab(self._build_key_hud_tab(), "按鍵顯示")
    tabs.addTab(self._build_find_cursor_tab(), "尋找游標")

    apply_button = QPushButton("套用")
    apply_button.clicked.connect(self._apply)

    layout = QVBoxLayout(self)
    layout.addWidget(tabs)
    layout.addWidget(apply_button)

  def _build_spotlight_tab(self) -> QWidget:
    widget = QWidget()
    form = QFormLayout(widget)

    self._spotlight_mode = QComboBox()
    self._spotlight_mode.addItems(["circle", "spotlight"])
    self._spotlight_mode.setCurrentText(self._config.spotlight.mode)
    form.addRow("模式", self._spotlight_mode)

    self._spotlight_color = self._build_color_picker(self._config.spotlight.color)
    form.addRow("顏色", self._spotlight_color)

    self._spotlight_radius = QSpinBox()
    self._spotlight_radius.setRange(10, 400)
    self._spotlight_radius.setValue(self._config.spotlight.radius)
    form.addRow("半徑", self._spotlight_radius)

    self._spotlight_circle_opacity = QDoubleSpinBox()
    self._spotlight_circle_opacity.setRange(0.05, 1.0)
    self._spotlight_circle_opacity.setSingleStep(0.05)
    self._spotlight_circle_opacity.setValue(self._config.spotlight.circle_opacity)
    self._spotlight_circle_opacity.setToolTip("circle 模式下色圈本身的透明度")
    form.addRow("色圈透明度", self._spotlight_circle_opacity)

    self._spotlight_dim = QDoubleSpinBox()
    self._spotlight_dim.setRange(0.0, 1.0)
    self._spotlight_dim.setSingleStep(0.05)
    self._spotlight_dim.setValue(self._config.spotlight.dim_opacity)
    form.addRow("暗化透明度", self._spotlight_dim)

    self._spotlight_smoothing = QDoubleSpinBox()
    self._spotlight_smoothing.setRange(0.05, 1.0)
    self._spotlight_smoothing.setSingleStep(0.05)
    self._spotlight_smoothing.setValue(self._config.spotlight.follow_smoothing)
    self._spotlight_smoothing.setToolTip("越小跟隨越平滑滯後；與游標的距離永遠不超過半徑大小")
    form.addRow("跟隨平滑係數", self._spotlight_smoothing)

    return widget

  def _build_click_effect_tab(self) -> QWidget:
    widget = QWidget()
    form = QFormLayout(widget)

    self._left_color = self._build_color_picker(self._config.click_effect.left_color)
    form.addRow("左鍵顏色", self._left_color)

    self._right_color = self._build_color_picker(self._config.click_effect.right_color)
    form.addRow("右鍵顏色", self._right_color)

    self._click_max_radius = QSpinBox()
    self._click_max_radius.setRange(10, 300)
    self._click_max_radius.setValue(self._config.click_effect.max_radius)
    form.addRow("最大半徑", self._click_max_radius)

    self._click_duration = QSpinBox()
    self._click_duration.setRange(100, 2000)
    self._click_duration.setValue(self._config.click_effect.duration_ms)
    form.addRow("動畫時長 (ms)", self._click_duration)

    return widget

  def _build_key_hud_tab(self) -> QWidget:
    widget = QWidget()
    form = QFormLayout(widget)

    self._hud_corner = QComboBox()
    for value, label in _HUD_POSITIONS:
      self._hud_corner.addItem(label, value)
    current_index = self._hud_corner.findData(self._config.key_hud.corner)
    self._hud_corner.setCurrentIndex(current_index if current_index >= 0 else 0)
    form.addRow("顯示位置", self._hud_corner)

    self._hud_font_size = QSpinBox()
    self._hud_font_size.setRange(10, 60)
    self._hud_font_size.setValue(self._config.key_hud.font_size)
    form.addRow("字體大小", self._hud_font_size)

    self._hud_fade = QSpinBox()
    self._hud_fade.setRange(200, 5000)
    self._hud_fade.setValue(self._config.key_hud.fade_duration_ms)
    form.addRow("淡出時間 (ms)", self._hud_fade)

    self._hud_max_badges = QSpinBox()
    self._hud_max_badges.setRange(1, 10)
    self._hud_max_badges.setValue(self._config.key_hud.max_visible_badges)
    form.addRow("最多顯示筆數", self._hud_max_badges)

    self._hud_show_mouse = QCheckBox()
    self._hud_show_mouse.setChecked(self._config.key_hud.show_mouse_buttons)
    form.addRow("顯示滑鼠按鈕", self._hud_show_mouse)

    return widget

  def _build_find_cursor_tab(self) -> QWidget:
    widget = QWidget()
    form = QFormLayout(widget)

    self._hotkey_edit = QLineEdit(self._config.find_cursor.trigger_hotkey)
    form.addRow("觸發熱鍵", self._hotkey_edit)

    self._shake_enabled = QCheckBox()
    self._shake_enabled.setChecked(self._config.find_cursor.shake_detection_enabled)
    form.addRow("啟用搖晃偵測", self._shake_enabled)

    self._effect_style = QComboBox()
    self._effect_style.addItems(["crosshair", "pulse_circle", "both"])
    self._effect_style.setCurrentText(self._config.find_cursor.effect_style)
    form.addRow("效果樣式", self._effect_style)

    self._effect_duration = QSpinBox()
    self._effect_duration.setRange(500, 6000)
    self._effect_duration.setValue(self._config.find_cursor.effect_duration_ms)
    form.addRow("效果持續時間 (ms)", self._effect_duration)

    self._play_sound = QCheckBox()
    self._play_sound.setChecked(self._config.find_cursor.play_sound)
    form.addRow("播放提示音", self._play_sound)

    return widget

  def _build_color_picker(self, initial_color: str) -> QPushButton:
    button = QPushButton(initial_color)
    button.setProperty("color_value", initial_color)

    def pick_color() -> None:
      color = QColorDialog.getColor(QColor(button.property("color_value")), self)
      if color.isValid():
        button.setProperty("color_value", color.name())
        button.setText(color.name())

    button.clicked.connect(pick_color)
    return button

  def _apply(self) -> None:
    new_config = replace(
      self._config,
      spotlight=replace(
        self._config.spotlight,
        mode=self._spotlight_mode.currentText(),
        color=self._spotlight_color.property("color_value"),
        radius=self._spotlight_radius.value(),
        circle_opacity=self._spotlight_circle_opacity.value(),
        dim_opacity=self._spotlight_dim.value(),
        follow_smoothing=self._spotlight_smoothing.value(),
      ),
      click_effect=replace(
        self._config.click_effect,
        left_color=self._left_color.property("color_value"),
        right_color=self._right_color.property("color_value"),
        max_radius=self._click_max_radius.value(),
        duration_ms=self._click_duration.value(),
      ),
      key_hud=replace(
        self._config.key_hud,
        corner=self._hud_corner.currentData(),
        font_size=self._hud_font_size.value(),
        fade_duration_ms=self._hud_fade.value(),
        max_visible_badges=self._hud_max_badges.value(),
        show_mouse_buttons=self._hud_show_mouse.isChecked(),
      ),
      find_cursor=replace(
        self._config.find_cursor,
        trigger_hotkey=self._hotkey_edit.text(),
        shake_detection_enabled=self._shake_enabled.isChecked(),
        effect_style=self._effect_style.currentText(),
        effect_duration_ms=self._effect_duration.value(),
        play_sound=self._play_sound.isChecked(),
      ),
    )
    self._on_apply(new_config)
