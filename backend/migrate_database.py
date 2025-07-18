#!/usr/bin/env python3
"""
数据库迁移脚本 - 为现有游戏设置正确的current_phase值
"""

import sys
import os
import asyncio

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_db, engine
from app.models.round_model import Round
from app.models.game import Game
from sqlalchemy import text

async def migrate_existing_games():
    """迁移现有游戏数据"""
    print("🔄 开始迁移现有游戏数据...")
    
    db = next(get_db())
    try:
        # 查找所有现有的轮次
        rounds = db.query(Round).all()
        
        if not rounds:
            print("✅ 没有现有的轮次数据需要迁移")
            return
        
        print(f"📊 发现 {len(rounds)} 个轮次需要迁移")
        
        for round_obj in rounds:
            round_id = getattr(round_obj, 'id', 0)
            status = getattr(round_obj, 'status', 'preparing')
            game_id = getattr(round_obj, 'game_id', 0)
            
            # 根据轮次状态推断current_phase
            if status == "preparing":
                current_phase = "preparing"
            elif status == "chatting":
                current_phase = "chatting"
            elif status == "voting":
                # 投票阶段，默认设为初投票（保守策略）
                current_phase = "initial_voting"
            elif status == "finished":
                current_phase = "finished"
            else:
                current_phase = "preparing"
            
            # 更新current_phase
            db.query(Round).filter(Round.id == round_id).update({
                "current_phase": current_phase
            })
            
            print(f"  轮次 {round_id} (游戏 {game_id}): {status} -> {current_phase}")
        
        db.commit()
        print("✅ 现有游戏数据迁移完成")
        
        # 显示迁移后的统计
        phase_counts = {}
        for round_obj in db.query(Round).all():
            phase = getattr(round_obj, 'current_phase', 'unknown')
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
        
        print("📈 迁移后的阶段分布:")
        for phase, count in phase_counts.items():
            print(f"  {phase}: {count} 个轮次")
            
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        db.rollback()
    finally:
        db.close()

async def check_database_schema():
    """检查数据库结构"""
    print("🔍 检查数据库结构...")
    
    try:
        with engine.connect() as conn:
            # 检查rounds表的结构
            result = conn.execute(text("PRAGMA table_info(rounds)"))
            columns = [(row[1], row[2]) for row in result.fetchall()]
            
            print("📊 rounds表结构:")
            for col_name, col_type in columns:
                print(f"  {col_name}: {col_type}")
            
            # 检查是否有current_phase字段
            has_current_phase = any(col[0] == 'current_phase' for col in columns)
            
            if has_current_phase:
                print("✅ current_phase字段已存在")
                return True
            else:
                print("❌ current_phase字段不存在，需要先运行数据库初始化")
                return False
                
    except Exception as e:
        print(f"❌ 检查数据库结构失败: {e}")
        return False

async def main():
    """主函数"""
    print("🚀 启动数据库迁移工具")
    
    # 检查数据库结构
    if not await check_database_schema():
        print("⚠️ 请先启动服务器一次以初始化数据库结构")
        return
    
    # 迁移现有数据
    await migrate_existing_games()
    
    print("🎉 数据库迁移完成！")

if __name__ == "__main__":
    asyncio.run(main()) 