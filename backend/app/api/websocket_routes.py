"""
WebSocket API路由
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.websocket_service import WebSocketManager
from app.services.game_service import GameService
import json

router = APIRouter()

# 使用全局WebSocket连接管理器
_manager = None

def get_websocket_manager():
    """获取全局WebSocket管理器实例"""
    global _manager
    if _manager is None:
        _manager = WebSocketManager()
    return _manager

@router.websocket("/game/{game_id}")
async def websocket_game_endpoint(
    websocket: WebSocket, 
    game_id: int,
    db: Session = Depends(get_db)
):
    """游戏WebSocket连接端点"""
    manager = get_websocket_manager()
    
    # 设置WebSocket ping/pong参数，增强连接稳定性
    websocket.client_state = websocket.client_state  # 确保连接状态正确
    
    await manager.connect(websocket, game_id)
    
    try:
        # 发送欢迎消息
        await manager.send_personal_message({
            "type": "connected",
            "message": f"已连接到游戏 {game_id}",
            "game_id": game_id
        }, websocket)
        
        # 检查并发送最新的系统消息（如果有的话）
        try:
            from app.services.game_service import GameService
            game_service = GameService(db)
            
            # 获取最新的轮次
            from app.models.round_model import Round
            latest_round = db.query(Round).filter(
                Round.game_id == game_id
            ).order_by(Round.round_number.desc()).first()
            
            if latest_round:
                # 获取该轮次最新的系统消息
                from app.models.message import Message
                latest_system_message = db.query(Message).filter(
                    Message.round_id == latest_round.id,
                    Message.message_type == "system"
                ).order_by(Message.timestamp.desc()).first()
                
                if latest_system_message:
                    print(f"🔄 向新连接发送最新系统消息: {latest_system_message.content[:50]}...")
                    await manager.send_personal_message({
                        "type": "system_message",
                        "message_id": f"reconnect_{latest_system_message.id}",
                        "content": latest_system_message.content,
                        "timestamp": latest_system_message.timestamp.isoformat() + 'Z'
                    }, websocket)
        except Exception as e:
            print(f"⚠️ 发送最新系统消息失败: {e}")
        
        # 监听消息
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # 处理不同类型的消息
                if message_data["type"] == "ping":
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": message_data.get("timestamp")
                    }, websocket)
                    print(f"💓 游戏 {game_id} 心跳响应")
                    continue  # 心跳处理完成，继续监听
                
                elif message_data["type"] == "observer_join":
                    # 观察者加入
                    await manager.broadcast_to_game({
                        "type": "observer_joined",
                        "message": "新观察者加入游戏"
                    }, game_id)
                    
                elif message_data["type"] == "get_game_status":
                    # 请求游戏状态
                    game_service = GameService(db)
                    status = await game_service.get_game_status(game_id)
                    if status:
                        await manager.send_personal_message({
                            "type": "game_status",
                            "status": status.model_dump() if hasattr(status, 'model_dump') else status.__dict__
                        }, websocket)
                
                # 其他消息类型的处理...
                
            except json.JSONDecodeError:
                print(f"收到无效JSON消息: {data}")
                continue
            except Exception as msg_error:
                error_msg = str(msg_error)
                # 检查是否是连接断开相关的错误
                if ("disconnect" in error_msg.lower() or 
                    "connection" in error_msg.lower() or 
                    "closed" in error_msg.lower()):
                    print(f"连接已断开: {msg_error}")
                    break  # 退出循环，让外层异常处理进行清理
                else:
                    print(f"处理消息时出错: {msg_error}")
                    continue
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, game_id)
        await manager.broadcast_to_game({
            "type": "observer_left",
            "message": "观察者离开游戏"
        }, game_id)
    except Exception as e:
        print(f"WebSocket错误: {e}")
        manager.disconnect(websocket, game_id)

@router.websocket("/admin/{game_id}")
async def websocket_admin_endpoint(
    websocket: WebSocket,
    game_id: int,
    db: Session = Depends(get_db)
):
    """管理员WebSocket连接端点"""
    manager = get_websocket_manager()
    await manager.connect_admin(websocket, game_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            admin_command = json.loads(data)
            
            # 处理管理员命令
            if admin_command["type"] == "start_round":
                game_service = GameService(db)
                await game_service.start_new_round(game_id)
                
            elif admin_command["type"] == "force_vote":
                game_service = GameService(db)
                await game_service.start_voting_phase(game_id)
                
            # 其他管理命令...
            
    except WebSocketDisconnect:
        manager.disconnect_admin(websocket, game_id)
    except Exception as e:
        print(f"管理员WebSocket错误: {e}")
        manager.disconnect_admin(websocket, game_id) 