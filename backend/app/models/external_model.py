"""
外部AI模型数据模型
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from app.core.database import Base

class ExternalModel(Base):
    """外部AI模型表"""
    __tablename__ = "external_models"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)  # 自定义显示名称
    api_url = Column(String(500), nullable=False)           # OpenWebUI API地址
    model_id = Column(String(200), nullable=False)          # 实际模型ID
    api_key = Column(String(500), nullable=True)            # API密钥（可选）
    description = Column(Text, nullable=True)               # 模型描述
    is_active = Column(Boolean, default=True)               # 是否启用
    last_tested = Column(DateTime(timezone=True), nullable=True)  # 最后测试时间
    test_status = Column(String(20), nullable=True)         # 测试状态：success, failed, pending
    test_error = Column(Text, nullable=True)                # 测试错误信息
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 