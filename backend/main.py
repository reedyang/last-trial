#!/usr/bin/env python3
"""
2050：最终审判 - 后端主入口
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import api_router
from app.core.database import init_db

app = FastAPI(
    title="2050：最终审判",
    description="基于Ollama的多2050：最终审判后端API",
    version="1.0.0"
)

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 前端开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    print("🚀 启动2050：最终审判后端服务...")
    await init_db()
    print("✅ 数据库初始化完成")
    
    # 恢复中断的游戏
    try:
        from app.core.database import get_db
        from app.services.game_service import GameService
        
        # 获取数据库会话
        db = next(get_db())
        game_service = GameService(db)
        
        # 恢复中断的游戏
        await game_service.resume_interrupted_games()
        
        # 关闭数据库会话
        db.close()
        
    except Exception as e:
        print(f"⚠️ 游戏恢复过程中出现错误: {e}")
        print("🔄 服务器将继续启动，但中断的游戏可能需要手动重启")

@app.get("/")
async def root():
    """根路径健康检查"""
    return {"message": "2050：最终审判后端运行中", "status": "healthy"}

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": "ai-chat-elimination-game"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    ) 