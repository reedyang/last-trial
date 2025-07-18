"""
游戏数据模型
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Game(Base):
    """游戏会话表"""
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True, index=True)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="preparing")  # preparing, running, finished, cancelled
    settings = Column(Text)  # JSON格式的游戏设置
    winner_count = Column(Integer, default=0)
    total_rounds = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    participants = relationship("Participant", back_populates="game") 