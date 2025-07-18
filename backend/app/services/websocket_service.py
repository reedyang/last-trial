"""
WebSocket连接管理服务
"""

from fastapi import WebSocket
from typing import Dict, List
import json

class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 游戏观察者连接
        self.game_connections: Dict[int, List[WebSocket]] = {}
        # 管理员连接
        self.admin_connections: Dict[int, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, game_id: int):
        """连接观察者WebSocket"""
        await websocket.accept()
        if game_id not in self.game_connections:
            self.game_connections[game_id] = []
        
        # 检查是否已存在，避免重复连接
        if websocket not in self.game_connections[game_id]:
            self.game_connections[game_id].append(websocket)
            print(f"新连接加入游戏 {game_id}，当前连接数: {len(self.game_connections[game_id])}")
    
    async def connect_admin(self, websocket: WebSocket, game_id: int):
        """连接管理员WebSocket"""
        await websocket.accept()
        self.admin_connections[game_id] = websocket
    
    def disconnect(self, websocket: WebSocket, game_id: int):
        """断开观察者连接"""
        if game_id in self.game_connections:
            if websocket in self.game_connections[game_id]:
                self.game_connections[game_id].remove(websocket)
                print(f"连接断开游戏 {game_id}，当前连接数: {len(self.game_connections[game_id])}")
    
    def disconnect_admin(self, websocket: WebSocket, game_id: int):
        """断开管理员连接"""
        if game_id in self.admin_connections:
            if self.admin_connections[game_id] == websocket:
                del self.admin_connections[game_id]
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            print(f"发送个人消息失败: {e}")
    
    async def broadcast_to_game(self, message: dict, game_id: int):
        """向游戏中的所有观察者广播消息"""
        if game_id not in self.game_connections:
            print(f"⚠️ 游戏 {game_id} 没有WebSocket连接，跳过广播")
            return
        
        connections = self.game_connections[game_id].copy()  # 创建副本进行迭代
        if not connections:
            print(f"⚠️ 游戏 {game_id} 没有活跃连接，跳过广播")
            return
            
        print(f"📡 向游戏 {game_id} 的 {len(connections)} 个连接广播消息类型: {message.get('type', 'unknown')}")
        
        message_text = json.dumps(message, ensure_ascii=False)
        failed_connections = []
        success_count = 0
        
        for connection in connections:
            try:
                await connection.send_text(message_text)
                success_count += 1
            except Exception as e:
                print(f"广播消息失败: {e}")
                failed_connections.append(connection)
        
        # 移除失败的连接
        for failed_connection in failed_connections:
            if failed_connection in self.game_connections[game_id]:
                self.game_connections[game_id].remove(failed_connection)
        
        if failed_connections:
            print(f"移除 {len(failed_connections)} 个失效连接，剩余连接数: {len(self.game_connections[game_id])}")
        
        print(f"✅ 广播完成: {success_count} 成功, {len(failed_connections)} 失败")
    
    async def send_to_admin(self, message: dict, game_id: int):
        """发送消息给管理员"""
        if game_id in self.admin_connections:
            try:
                await self.admin_connections[game_id].send_text(
                    json.dumps(message, ensure_ascii=False)
                )
            except Exception as e:
                print(f"发送管理员消息失败: {e}")
                # 连接已断开，移除
                del self.admin_connections[game_id] 