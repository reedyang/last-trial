#!/usr/bin/env python3
"""
数据库迁移脚本：为外部模型表添加API类型字段
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def migrate_add_api_type():
    """添加API类型字段的迁移"""
    
    print("🚀 开始执行外部模型API类型字段迁移...")
    
    # 创建数据库引擎
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # 检查表是否存在
            result = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='external_models'
            """)).fetchone()
            
            if not result:
                print("⚠️ external_models表不存在，跳过迁移")
                return
            
            # 检查字段是否已存在
            result = conn.execute(text("PRAGMA table_info(external_models)")).fetchall()
            columns = [row[1] for row in result]
            
            if 'api_type' in columns:
                print("✅ api_type字段已存在，跳过迁移")
                return
            
            print("📝 添加api_type字段...")
            
            # SQLite不支持ALTER TABLE ADD COLUMN WITH DEFAULT ENUM
            # 我们需要重建表
            
            # 1. 创建新表结构
            conn.execute(text("""
                CREATE TABLE external_models_new (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    api_type VARCHAR(20) NOT NULL DEFAULT 'openwebui',
                    api_url VARCHAR(500) NOT NULL,
                    model_id VARCHAR(200) NOT NULL,
                    api_key VARCHAR(500),
                    description TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    last_tested DATETIME,
                    test_status VARCHAR(20),
                    test_error TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME
                )
            """))
            
            # 2. 复制数据（为所有现有记录设置默认的api_type为'openwebui'）
            conn.execute(text("""
                INSERT INTO external_models_new 
                (id, name, api_type, api_url, model_id, api_key, description, 
                 is_active, last_tested, test_status, test_error, created_at, updated_at)
                SELECT id, name, 'openwebui', api_url, model_id, api_key, description,
                       is_active, last_tested, test_status, test_error, created_at, updated_at
                FROM external_models
            """))
            
            # 3. 删除旧表
            conn.execute(text("DROP TABLE external_models"))
            
            # 4. 重命名新表
            conn.execute(text("ALTER TABLE external_models_new RENAME TO external_models"))
            
            # 5. 提交更改
            conn.commit()
            
            print("✅ 成功添加api_type字段，所有现有模型默认设置为OpenWebUI类型")
            
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        raise
    
    print("🎉 迁移完成！")

if __name__ == "__main__":
    migrate_add_api_type() 