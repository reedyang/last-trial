"""
应用配置模块
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """应用设置"""
    
    # 基础设置
    APP_NAME: str = "2050：最终审判"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 服务器设置
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    
    # 数据库设置
    DATABASE_URL: str = "sqlite:///./ai_game.db"
    
    # Ollama设置
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_TIMEOUT: int = 60
    
    # 游戏设置
    MAX_ROUND_TIME: int = 300  # 每轮最大时间（秒）
    MAX_MESSAGE_LENGTH: int = 500  # 最大消息长度
    MIN_PARTICIPANTS: int = 3  # 最少参与者数量
    
    # WebSocket设置
    WS_HEARTBEAT_INTERVAL: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 全局设置实例
settings = Settings() 