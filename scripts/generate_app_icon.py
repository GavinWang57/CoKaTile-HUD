"""把 assets/tray_icon.png 轉成打包執行檔用的 .ico（Windows 的 exe 圖示僅接受 ICO 格式）。

僅打包時需要，屬建置期工具，需要額外安裝 Pillow：

    pip install pillow
    python scripts/generate_app_icon.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

_SOURCE_PATH = Path(__file__).resolve().parent.parent / "assets" / "tray_icon.png"
_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "assets" / "app_icon.ico"
_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main() -> None:
  image = Image.open(_SOURCE_PATH).convert("RGBA")
  image.save(_OUTPUT_PATH, format="ICO", sizes=_SIZES)
  print(f"已產生圖示：{_OUTPUT_PATH}")


if __name__ == "__main__":
  main()
