"""
游戏管理API路由
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.services.game_service import GameService
from app.schemas.game_schemas import GameCreate, GameResponse, GameStatus

router = APIRouter()

@router.post("/create", response_model=GameResponse)
async def create_game(
    game_data: GameCreate,
    db: Session = Depends(get_db)
):
    """创建新游戏"""
    game_service = GameService(db)
    try:
        game = await game_service.create_game(game_data)
        return game
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{game_id}", response_model=GameResponse)
async def get_game(
    game_id: int,
    db: Session = Depends(get_db)
):
    """获取游戏信息"""
    game_service = GameService(db)
    game = await game_service.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="游戏不存在")
    return game

@router.get("/{game_id}/messages")
async def get_game_messages(
    game_id: int,
    db: Session = Depends(get_db)
):
    """获取游戏的历史聊天记录"""
    game_service = GameService(db)
    try:
        messages = await game_service.get_game_messages(game_id)
        return messages
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{game_id}")
async def delete_game(
    game_id: int,
    db: Session = Depends(get_db)
):
    """删除游戏"""
    game_service = GameService(db)
    try:
        await game_service.delete_game(game_id)
        return {"message": "游戏已删除", "game_id": game_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{game_id}/start")
async def start_game(
    game_id: int,
    db: Session = Depends(get_db)
):
    """开始游戏"""
    game_service = GameService(db)
    try:
        result = await game_service.start_game(game_id)
        return {"message": "游戏已开始", "game_id": game_id, "participants": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{game_id}/stop")
async def stop_game(
    game_id: int,
    db: Session = Depends(get_db)
):
    """停止游戏"""
    game_service = GameService(db)
    try:
        await game_service.stop_game(game_id)
        return {"message": "游戏已停止", "game_id": game_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{game_id}/status", response_model=GameStatus)
async def get_game_status(
    game_id: int,
    db: Session = Depends(get_db)
):
    """获取游戏状态"""
    game_service = GameService(db)
    status = await game_service.get_game_status(game_id)
    if not status:
        raise HTTPException(status_code=404, detail="游戏不存在")
    return status

@router.get("/")
async def list_games(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """获取游戏列表"""
    game_service = GameService(db)
    games = await game_service.list_games(skip=skip, limit=limit)
    return games 