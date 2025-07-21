"""
外部AI模型相关的数据模式
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime

class ExternalModelCreate(BaseModel):
    """创建外部模型的请求"""
    name: str = Field(..., min_length=1, max_length=100, description="自定义显示名称")
    api_url: str = Field(..., description="OpenWebUI API地址")
    model_id: str = Field(..., min_length=1, max_length=200, description="实际模型ID")
    api_key: Optional[str] = Field(None, description="API密钥（可选）")
    description: Optional[str] = Field(None, description="模型描述")
    is_active: bool = Field(True, description="是否启用")

class ExternalModelUpdate(BaseModel):
    """更新外部模型的请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="自定义显示名称")
    api_url: Optional[str] = Field(None, description="OpenWebUI API地址")
    model_id: Optional[str] = Field(None, min_length=1, max_length=200, description="实际模型ID")
    api_key: Optional[str] = Field(None, description="API密钥（可选）")
    description: Optional[str] = Field(None, description="模型描述")
    is_active: Optional[bool] = Field(None, description="是否启用")

class ExternalModelResponse(BaseModel):
    """外部模型的响应"""
    id: int
    name: str
    api_url: str
    model_id: str
    api_key: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    last_tested: Optional[datetime] = None
    test_status: Optional[str] = None
    test_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ExternalModelTest(BaseModel):
    """测试外部模型的请求"""
    api_url: str = Field(..., description="OpenWebUI API地址")
    model_id: str = Field(..., description="模型ID")
    api_key: Optional[str] = Field(None, description="API密钥（可选）")

class ExternalModelTestResponse(BaseModel):
    """测试外部模型的响应"""
    success: bool
    message: str
    response_time: Optional[float] = None
    error: Optional[str] = None 