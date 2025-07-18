"""
淘汰记录数据模型
"""

from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Elimination(Base):
    """淘汰记录表"""
    __tablename__ = "eliminations"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=False)
    round_number = Column(Integer, nullable=False)     # 被淘汰的轮次
    vote_count = Column(Integer, nullable=False)       # 得票数
    elimination_time = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    game = relationship("Game")
    participant = relationship("Participant") 