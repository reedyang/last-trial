"""
参与者数据模型
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Participant(Base):
    """AI参与者表"""
    __tablename__ = "participants"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    model_name = Column(String(100), nullable=False)  # Ollama模型名称
    human_name = Column(String(50), nullable=False)   # 分配的人类姓名
    background = Column(Text)                         # 角色背景设定
    personality = Column(String(100))                 # 性格特征
    role = Column(String(20), default="human_survivor") # ai_spy, human_survivor
    status = Column(String(20), default="active")     # active, eliminated, winner
    elimination_round = Column(Integer, nullable=True) # 被淘汰的轮次
    final_rank = Column(Integer, nullable=True)        # 最终排名
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    game = relationship("Game", back_populates="participants") 