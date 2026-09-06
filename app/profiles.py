"""教學模式／日常模式的預設參數組合。"""
from __future__ import annotations

from dataclasses import replace

from app.config import AppConfig

PROFILE_TEACHING = "teaching"
PROFILE_DAILY = "daily"


def apply_profile(config: AppConfig, profile: str) -> AppConfig:
  """回傳套用指定情境預設後的新設定（不修改原物件），套用後個別功能仍可事後手動調整。"""
  if profile == PROFILE_TEACHING:
    return replace(
      config,
      active_profile=PROFILE_TEACHING,
      spotlight=replace(config.spotlight, enabled=True, mode="spotlight", radius=120, dim_opacity=0.6),
      click_effect=replace(config.click_effect, enabled=True),
      key_hud=replace(config.key_hud, enabled=True),
      find_cursor=replace(config.find_cursor, enabled=True),
    )
  return replace(
    config,
    active_profile=PROFILE_DAILY,
    spotlight=replace(config.spotlight, enabled=True, mode="circle", radius=45, dim_opacity=0.6),
    click_effect=replace(config.click_effect, enabled=False),
    key_hud=replace(config.key_hud, enabled=False),
    find_cursor=replace(config.find_cursor, enabled=True),
  )
