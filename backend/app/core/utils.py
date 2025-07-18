"""
工具函数模块
"""

from typing import Optional
from datetime import datetime


def format_timestamp_with_timezone(timestamp: Optional[datetime]) -> str:
    """格式化时间戳，确保包含UTC时区标识符"""
    if not timestamp:
        return ""
    # 确保发送给前端的时间戳包含'Z'后缀，表示这是UTC时间
    return timestamp.isoformat() + 'Z' 