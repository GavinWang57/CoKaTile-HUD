"""CoKaTile HUD 進入點。"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.app_context import AppContext
from app.version import APP_NAME, APP_VERSION


def main() -> int:
  app = QApplication(sys.argv)
  app.setApplicationName(APP_NAME)
  app.setApplicationVersion(APP_VERSION)
  app.setQuitOnLastWindowClosed(False)
  context = AppContext()
  return app.exec()


if __name__ == "__main__":
  sys.exit(main())
