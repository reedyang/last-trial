#!/usr/bin/env python3
"""
调试脚本：检查时间戳格式
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, DateTime, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

# 模拟数据库配置
engine = create_engine("sqlite:///debug_time.db")
Base = declarative_base()

class TestMessage(Base):
    __tablename__ = "test_messages"
    
    id = Column(Integer, primary_key=True)
    content = Column(String(100))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

# 创建表
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def test_timestamp_formats():
    session = Session()
    
    # 创建一条测试记录
    test_msg = TestMessage(content="测试消息")
    session.add(test_msg)
    session.commit()
    session.refresh(test_msg)
    
    # 获取时间戳
    timestamp = test_msg.timestamp
    
    print("=" * 50)
    print("时间戳格式测试")
    print("=" * 50)
    print(f"数据库存储的时间戳类型: {type(timestamp)}")
    print(f"数据库存储的时间戳值: {timestamp}")
    print(f"时间戳的时区信息: {timestamp.tzinfo}")
    print(f"isoformat()输出: {timestamp.isoformat()}")
    print(f"isoformat()类型: {type(timestamp.isoformat())}")
    
    # 测试不同的格式化方式
    print("\n不同格式化方式:")
    print(f"str(timestamp): {str(timestamp)}")
    print(f"timestamp.strftime('%Y-%m-%d %H:%M:%S'): {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 测试当前时间
    now = datetime.now()
    utc_now = datetime.utcnow()
    
    print(f"\ndatetime.now(): {now}")
    print(f"datetime.now().isoformat(): {now.isoformat()}")
    print(f"datetime.utcnow(): {utc_now}")
    print(f"datetime.utcnow().isoformat(): {utc_now.isoformat()}")
    
    session.close()

if __name__ == "__main__":
    test_timestamp_formats() 