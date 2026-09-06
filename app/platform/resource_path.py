"""解析靜態資源（如圖示）的實際路徑，同時支援開發環境與 PyInstaller 打包後的執行檔。"""
from __future__ import annotations

import sys
from pathlib import Path


def resource_path(*parts: str) -> Path:
  if hasattr(sys, "_MEIPASS"):
    base = Path(sys._MEIPASS)  # PyInstaller 執行時解壓縮資源的暫存目錄
  else:
    base = Path(__file__).resolve().parent.parent.parent  # 專案根目錄
  return base.joinpath(*parts)
