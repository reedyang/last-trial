"""
游戏相关的数据模式
"""

from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List
from datetime import datetime

class GameCreate(BaseModel):
    """创建游戏的请求模式"""
    max_round_time: int = Field(default=300, description="每轮最大时间（秒）")
    selected_models: Optional[List[str]] = Field(default=None, description="选择的模型列表")

class GameResponse(BaseModel):
    """游戏响应模式"""
    id: int
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_rounds: int
    winner_count: int
    created_at: datetime
    
    @field_serializer('start_time', 'end_time', 'created_at')
    def serialize_dt(self, dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        return dt.isoformat() + 'Z'
    
    class Config:
        from_attributes = True

class ParticipantInfo(BaseModel):
    """参与者信息"""
    id: int
    model_name: str
    human_name: str
    background: str
    personality: str
    status: str
    elimination_round: Optional[int] = None
    
    class Config:
        from_attributes = True

class GameStatus(BaseModel):
    """游戏状态"""
    game_id: int
    status: str
    current_round: int
    participants: List[ParticipantInfo]
    active_participants: int
    eliminated_participants: int
    
class RoundInfo(BaseModel):
    """轮次信息"""
    id: int
    round_number: int
    topic: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    
    @field_serializer('start_time', 'end_time')
    def serialize_dt(self, dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        return dt.isoformat() + 'Z'
    
    class Config:
        from_attributes = True 