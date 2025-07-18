"""
投票数据模型
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Vote(Base):
    """投票表"""
    __tablename__ = "votes"
    
    id = Column(Integer, primary_key=True, index=True)
    round_id = Column(Integer, ForeignKey("rounds.id"), nullable=False)
    voter_id = Column(Integer, ForeignKey("participants.id"), nullable=False)      # 投票者
    target_id = Column(Integer, ForeignKey("participants.id"), nullable=False)     # 被投票者
    vote_phase = Column(String(30), nullable=False, default="initial_voting")     # 投票阶段：initial_voting, final_voting, additional_voting
    reason = Column(Text, nullable=True)                                           # 投票理由
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    round = relationship("Round")
    voter = relationship("Participant", foreign_keys=[voter_id])
    target = relationship("Participant", foreign_keys=[target_id]) 