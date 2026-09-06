"""單一按鍵/按鈕徽章的資料結構。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class KeyBadge:
  key_id: str  # 穩定識別碼（如 "kb:ctrl"、"mouse:left"），與顯示文字分開避免格式影響配對
  display_text: str
  created_at: float
  released_at: float | None = None  # None 表示目前仍按住
  repeat_count: int = 1  # 短時間內重複按下（連點）的次數
