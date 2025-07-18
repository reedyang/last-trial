"""
API路由模块
"""

from fastapi import APIRouter
from .game_routes import router as game_router
from .ollama_routes import router as ollama_router
from .websocket_routes import router as ws_router

# 创建主路由器
api_router = APIRouter()

# 注册各个功能模块的路由
api_router.include_router(game_router, prefix="/game", tags=["游戏管理"])
api_router.include_router(ollama_router, prefix="/ollama", tags=["Ollama集成"])
api_router.include_router(ws_router, prefix="/ws", tags=["WebSocket"]) 