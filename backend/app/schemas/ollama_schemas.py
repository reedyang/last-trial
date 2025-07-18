"""
Ollama相关的数据模式
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ModelInfo(BaseModel):
    """模型信息"""
    name: str
    size: Optional[str] = None
    format: Optional[str] = None
    family: Optional[str] = None
    families: Optional[List[str]] = None
    parameter_size: Optional[str] = None
    quantization_level: Optional[str] = None

class ChatRequest(BaseModel):
    """聊天请求"""
    model: str = Field(..., description="模型名称")
    message: str = Field(..., description="消息内容")
    context: Optional[str] = Field(None, description="上下文信息")
    system_prompt: Optional[str] = Field(None, description="系统提示")
    max_tokens: Optional[int] = Field(500, description="最大token数")
    temperature: Optional[float] = Field(0.8, description="创造性温度")

class ChatResponse(BaseModel):
    """聊天响应"""
    model: str
    message: str
    done: bool
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None
    
class AIParticipantConfig(BaseModel):
    """AI参与者配置"""
    model_name: str
    human_name: str
    background: str
    personality: str
    system_prompt: str 