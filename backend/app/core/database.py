"""
数据库配置
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 数据库文件路径
DATABASE_URL = "sqlite:///./ai_game.db"

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},
    echo=False  # 设置为True可以看到SQL查询日志
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def init_db():
    """初始化数据库"""
    # 导入所有模型
    from app.models.game import Game
    from app.models.participant import Participant
    from app.models.round_model import Round
    from app.models.message import Message
    from app.models.elimination import Elimination
    from app.models.vote import Vote
    from app.models.external_model import ExternalModel
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    # 执行数据库迁移
    await _migrate_database()
    
    print("数据库初始化完成")

async def _migrate_database():
    """执行数据库迁移"""
    try:
        with engine.connect() as conn:
            # 检查current_phase字段是否存在
            result = conn.execute(text("PRAGMA table_info(rounds)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'current_phase' not in columns:
                print("📦 执行数据库迁移：添加current_phase字段...")
                conn.execute(text("ALTER TABLE rounds ADD COLUMN current_phase VARCHAR(30) DEFAULT 'preparing'"))
                conn.commit()
                print("✅ current_phase字段添加成功")
            else:
                print("✅ current_phase字段已存在，跳过迁移")
            
            # 检查vote_phase字段是否存在
            result = conn.execute(text("PRAGMA table_info(votes)"))
            vote_columns = [row[1] for row in result.fetchall()]
            
            if 'vote_phase' not in vote_columns:
                print("📦 执行数据库迁移：添加vote_phase字段...")
                conn.execute(text("ALTER TABLE votes ADD COLUMN vote_phase VARCHAR(30) DEFAULT 'initial_voting'"))
                conn.commit()
                print("✅ vote_phase字段添加成功")
                
                # 为现有投票记录设置默认阶段
                print("📦 更新现有投票记录的阶段信息...")
                conn.execute(text("UPDATE votes SET vote_phase = 'initial_voting' WHERE vote_phase IS NULL OR vote_phase = ''"))
                conn.commit()
                print("✅ 现有投票记录阶段信息更新完成")
            else:
                print("✅ vote_phase字段已存在，跳过迁移")
            
            # 检查message表的title字段是否存在
            result = conn.execute(text("PRAGMA table_info(messages)"))
            message_columns = [row[1] for row in result.fetchall()]
            
            if 'title' not in message_columns:
                print("📦 执行数据库迁移：添加message.title字段...")
                conn.execute(text("ALTER TABLE messages ADD COLUMN title VARCHAR(100)"))
                conn.commit()
                print("✅ message.title字段添加成功")
                
                # 为现有的voting_table类型消息设置默认标题
                print("📦 更新现有投票表格消息的标题...")
                conn.execute(text("UPDATE messages SET title = '投票结果' WHERE message_type = 'voting_table' AND (title IS NULL OR title = '')"))
                conn.commit()
                print("✅ 现有投票表格消息标题更新完成")
            else:
                print("✅ message.title字段已存在，跳过迁移")
                
    except Exception as e:
        print(f"⚠️ 数据库迁移出现错误: {e}")
        print("程序将继续运行，但某些新功能可能不可用") 