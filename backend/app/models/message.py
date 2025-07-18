"""
消息数据模型
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Message(Base):
    """对话消息表"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    round_id = Column(Integer, ForeignKey("rounds.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=True)  # 系统消息可以为空
    content = Column(Text, nullable=False)             # 消息内容
    message_type = Column(String(20), default="chat")  # chat, system, vote_reason, voting_table
    title = Column(String(100), nullable=True)         # 消息标题（用于投票表格等）
    sequence_number = Column(Integer)                  # 在本轮中的发言顺序
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    round = relationship("Round")
    participant = relationship("Participant") 