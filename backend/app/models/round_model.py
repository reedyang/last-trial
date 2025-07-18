"""
轮次数据模型
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Round(Base):
    """对话轮次表"""
    __tablename__ = "rounds"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    round_number = Column(Integer, nullable=False)     # 轮次编号
    topic = Column(Text)                               # 讨论话题
    status = Column(String(20), default="preparing")   # preparing, chatting, voting, finished
    current_phase = Column(String(30), default="preparing")  # 详细阶段：preparing, chatting, initial_voting, final_defense, final_voting, additional_debate, additional_voting, finished
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    eliminated_participant_id = Column(Integer, ForeignKey("participants.id"), nullable=True)
    
    # 关系
    game = relationship("Game")
    eliminated_participant = relationship("Participant") 