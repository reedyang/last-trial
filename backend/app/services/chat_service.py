"""
AI对话管理服务
"""

import asyncio
import random
import uuid
from typing import List, Optional, Any, Dict
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.game import Game
from app.models.participant import Participant
from app.models.round_model import Round
from app.models.message import Message
from app.services.ollama_service import OllamaService
from app.services.websocket_service import WebSocketManager
from sqlalchemy import func
from app.models.vote import Vote

class ChatService:
    """AI对话管理服务"""
    
    def __init__(self, db: Session, websocket_manager: WebSocketManager):
        self.db = db
        self.ollama_service = OllamaService(db)  # 传递数据库连接
        self.websocket_manager = websocket_manager
    
    def _format_timestamp_with_timezone(self, timestamp: Optional[datetime]) -> str:
        """格式化时间戳，确保包含UTC时区标识符"""
        if not timestamp:
            return ""
        # 确保发送给前端的时间戳包含'Z'后缀，表示这是UTC时间
        return timestamp.isoformat() + 'Z'
        
    # 法庭辩论话题池（2050年末世背景）
    CHAT_TOPICS = [
        "请为你的人类身份进行辩护，证明你不是AI间谍",
        "描述你在AI战争中失去的亲人朋友，展现人类的情感",
        "解释你对AI的仇恨从何而来，说出你的真实经历",
        "谈谈你童年的回忆，AI无法伪造的人类记忆",
        "描述人类的生理感受：饥饿、疼痛、疲劳是什么感觉",
        "说出你最恐惧的事情，人类独有的恐惧心理",
        "回忆战争前的美好时光，那些只有人类才能理解的快乐",
        "解释人类的直觉和第六感，这些AI永远无法模拟的能力",
        "谈谈梦境和潜意识，证明你有真正的人类意识",
        "描述爱情和友情，那些超越逻辑的人类情感纽带"
    ]

    async def start_chat_round(self, game_id: int, round_number: int) -> Optional[Any]:
        """开始新的对话轮次"""
        print(f"开始轮次 {round_number}，游戏 {game_id}")
        
        # 检查游戏是否存在且正在运行
        game = self.db.query(Game).filter(Game.id == game_id).first()
        if not game:
            return None
        
        game_status = getattr(game, 'status', '')
        if game_status != "running":
            return None
        
        # 获取活跃参与者
        participants = self.db.query(Participant).filter(
            Participant.game_id == game_id,
            Participant.status == "active"
        ).all()
        
        if len(participants) < 2:
            # 游戏结束
            await self._end_game(game_id)
            return None
        
        # 检查轮次是否已存在
        existing_round = self.db.query(Round).filter(
            Round.game_id == game_id,
            Round.round_number == round_number
        ).first()
        
        if existing_round:
            # 轮次已存在，更新话题和状态
            topic = random.choice(self.CHAT_TOPICS)
            self.db.query(Round).filter(Round.id == getattr(existing_round, 'id', 0)).update({
                "topic": topic,
                "status": "chatting",
                "current_phase": "chatting"
            })
            self.db.commit()
            round_obj = existing_round
            round_id = getattr(existing_round, 'id', 0)
            print(f"更新现有轮次 {round_number} 的话题为: {topic}")
        else:
            # 创建新轮次
            topic = random.choice(self.CHAT_TOPICS)
            round_obj = Round(
                game_id=game_id,
                round_number=round_number,
                topic=topic,
                status="chatting",
                current_phase="chatting"
            )
            self.db.add(round_obj)
            self.db.commit()
            self.db.refresh(round_obj)
            round_id = getattr(round_obj, 'id', 0)
            print(f"创建新轮次 {round_number} 的话题为: {topic}")
        
        # 广播轮次开始
        message_id = str(uuid.uuid4())
        print(f"广播轮次开始消息 {message_id} 到游戏 {game_id}")
        print(f"📝 广播话题: {topic}")
        
        # 保存轮次开始系统消息（现在统一使用start_chat_round）
        round_start_content = f"⚖️ 紧急法庭审判开始！辩论焦点：{topic}"
        await self._save_system_message(round_id, round_start_content, "system")
        
        # 立即广播系统消息
        system_message_id = str(uuid.uuid4())
        print(f"📢 准备广播系统消息: {round_start_content[:50]}...")
        
        # 短暂延迟，确保WebSocket连接稳定
        await asyncio.sleep(0.5)
        
        try:
            await self.websocket_manager.broadcast_to_game({
                "type": "system_message",
                "message_id": system_message_id,
                "content": round_start_content,
                "timestamp": datetime.now().isoformat() + 'Z'
            }, game_id)
            print(f"✅ 系统消息广播成功: {system_message_id}")
        except Exception as e:
            print(f"❌ 系统消息广播失败: {e}")
        
        await self.websocket_manager.broadcast_to_game({
            "type": "round_start",
            "message_id": message_id,
            "round_number": round_number,
            "topic": topic,
            "participants": len(participants)
        }, game_id)
        
        # 开始AI对话
        await self._run_ai_chat(round_id, participants, topic, game_id)
        
        return round_obj
    
    async def start_chat_round_with_intro(self, game_id: int, round_number: int, intro_content: str) -> Optional[Any]:
        """开始新的对话轮次（带有介绍消息）"""
        print(f"开始轮次 {round_number}，游戏 {game_id}（带介绍）")
        
        # 检查游戏是否存在且正在运行
        game = self.db.query(Game).filter(Game.id == game_id).first()
        if not game:
            return None
        
        game_status = getattr(game, 'status', '')
        if game_status != "running":
            return None
        
        # 获取活跃参与者
        participants = self.db.query(Participant).filter(
            Participant.game_id == game_id,
            Participant.status == "active"
        ).all()
        
        if len(participants) < 2:
            # 游戏结束
            await self._end_game(game_id)
            return None
        
        # 创建新轮次
        topic = random.choice(self.CHAT_TOPICS)
        round_obj = Round(
            game_id=game_id,
            round_number=round_number,
            topic=topic,
            status="chatting",
            current_phase="chatting"
        )
        self.db.add(round_obj)
        self.db.commit()
        self.db.refresh(round_obj)
        round_id = getattr(round_obj, 'id', 0)
        print(f"创建新轮次 {round_number} 的话题为: {topic}")
        
        # 保存介绍消息到数据库（从GameService传来的准备消息）
        await self._save_system_message(round_id, intro_content, "system")
        
        # 保存轮次开始系统消息到数据库
        round_start_content = f"⚖️ 紧急法庭审判开始！辩论焦点：{topic}"
        await self._save_system_message(round_id, round_start_content, "system")
        
        # 立即广播介绍消息
        intro_message_id = str(uuid.uuid4())
        print(f"📢 准备广播介绍消息: {intro_content[:50]}...")
        
        # 短暂延迟，确保WebSocket连接稳定
        await asyncio.sleep(0.5)
        
        try:
            await self.websocket_manager.broadcast_to_game({
                "type": "system_message",
                "message_id": intro_message_id,
                "content": intro_content,
                "timestamp": datetime.now().isoformat() + 'Z'
            }, game_id)
            print(f"✅ 介绍消息广播成功: {intro_message_id}")
        except Exception as e:
            print(f"❌ 介绍消息广播失败: {e}")
        
        # 立即广播轮次开始系统消息
        system_message_id = str(uuid.uuid4())
        print(f"📢 准备广播轮次开始系统消息: {round_start_content[:50]}...")
        try:
            await self.websocket_manager.broadcast_to_game({
                "type": "system_message",
                "message_id": system_message_id,
                "content": round_start_content,
                "timestamp": datetime.now().isoformat() + 'Z'
            }, game_id)
            print(f"✅ 轮次开始系统消息广播成功: {system_message_id}")
        except Exception as e:
            print(f"❌ 轮次开始系统消息广播失败: {e}")
        
        # 广播轮次开始（不重复广播介绍消息）
        message_id = str(uuid.uuid4())
        print(f"广播轮次开始消息 {message_id} 到游戏 {game_id}")
        print(f"📝 广播话题: {topic}")
        
        await self.websocket_manager.broadcast_to_game({
            "type": "round_start",
            "message_id": message_id,
            "round_number": round_number,
            "topic": topic,
            "participants": len(participants)
        }, game_id)
        
        # 开始AI对话
        await self._run_ai_chat(round_id, participants, topic, game_id)
        
        return round_obj
    
    async def resume_chat_round(self, round_id: int) -> Optional[Any]:
        """恢复现有轮次的对话（用于游戏恢复）"""
        round_obj = self.db.query(Round).filter(Round.id == round_id).first()
        if not round_obj:
            print(f"轮次 {round_id} 不存在，无法恢复")
            return None
        
        game_id = getattr(round_obj, 'game_id', 0)
        round_number = getattr(round_obj, 'round_number', 1)
        existing_topic = getattr(round_obj, 'topic', '')
        
        print(f"恢复轮次 {round_number} (ID: {round_id})，游戏 {game_id}，话题: {existing_topic}")
        
        # 检查游戏是否存在且正在运行
        game = self.db.query(Game).filter(Game.id == game_id).first()
        if not game:
            return None
        
        game_status = getattr(game, 'status', '')
        if game_status != "running":
            return None
        
        # 获取活跃参与者
        participants = self.db.query(Participant).filter(
            Participant.game_id == game_id,
            Participant.status == "active"
        ).all()
        
        if len(participants) < 2:
            # 游戏结束
            await self._end_game(game_id)
            return None
        
        # 更新轮次状态为对话中（确保状态正确）
        self.db.query(Round).filter(Round.id == round_id).update({
            "status": "chatting",
            "current_phase": "chatting"
        })
        self.db.commit()
        
        # 广播恢复轮次消息
        message_id = str(uuid.uuid4())
        print(f"广播轮次恢复消息 {message_id} 到游戏 {game_id}")
        print(f"📝 恢复的话题: '{existing_topic}' (长度: {len(existing_topic)})")
        
        # 如果话题为空，重新生成一个
        if not existing_topic or existing_topic.strip() == '':
            print("⚠️ 检测到空话题，重新生成...")
            existing_topic = random.choice(self.CHAT_TOPICS)
            # 更新数据库中的话题
            self.db.query(Round).filter(Round.id == round_id).update({
                "topic": existing_topic
            })
            self.db.commit()
            print(f"🔄 已更新话题为: {existing_topic}")
        
        # 保存恢复轮次的系统消息到数据库
        resume_content = f"⚖️ 继续中断的法庭审判从中断处恢复！辩论焦点：{existing_topic}"
        await self._save_system_message(round_id, resume_content, "system", -1)
        
        # 立即广播恢复系统消息
        resume_message_id = str(uuid.uuid4())
        print(f"📢 准备广播恢复系统消息: {resume_content[:50]}...")
        
        # 短暂延迟，确保WebSocket连接稳定
        await asyncio.sleep(0.5)
        
        try:
            await self.websocket_manager.broadcast_to_game({
                "type": "system_message",
                "message_id": resume_message_id,
                "content": resume_content,
                "timestamp": datetime.now().isoformat() + 'Z'
            }, game_id)
            print(f"✅ 恢复系统消息广播成功: {resume_message_id}")
        except Exception as e:
            print(f"❌ 恢复系统消息广播失败: {e}")
        
        await self.websocket_manager.broadcast_to_game({
            "type": "round_start",
            "message_id": message_id,
            "round_number": round_number,
            "topic": existing_topic,
            "participants": len(participants),
            "is_resume": True  # 标记这是恢复的轮次
        }, game_id)
        
        # 计算已经发言的次数，从中断处继续
        existing_messages = self.db.query(Message).filter(
            Message.round_id == round_id,
            Message.message_type == "chat"
        ).count()
        
        # 计算总发言次数（每人2次）
        speeches_per_person = 2
        total_speeches = len(participants) * speeches_per_person
        
        print(f"轮次 {round_number} 已有 {existing_messages} 条发言，总需 {total_speeches} 条发言")
        
        if existing_messages >= total_speeches:
            # 辩论已完成，直接进入投票阶段
            print(f"轮次 {round_number} 辩论已完成，直接进入投票阶段")
            await self._simulate_ai_voting(round_id)
        else:
            # 继续AI对话（从中断处开始）
            print(f"轮次 {round_number} 从第 {existing_messages + 1} 条发言继续")
            await self._resume_ai_chat(round_id, participants, existing_topic, game_id, existing_messages)
        
        return round_obj
    
    async def _run_ai_chat(self, round_id: int, participants: List[Any], topic: str, game_id: int):
        """运行AI对话 - 基于时间控制的法庭辩论"""
        # 获取游戏设置中的时间限制
        game = self.db.query(Game).filter(Game.id == game_id).first()
        max_round_time = 600  # 默认10分钟
        
        if game and getattr(game, 'settings', None):
            try:
                import json
                settings = json.loads(getattr(game, 'settings', '{}'))
                max_round_time = settings.get('max_round_time', 600)
                print(f"📅 获取到游戏设置的辩论时间: {max_round_time}秒 ({max_round_time//60}分{max_round_time%60}秒)")
            except (json.JSONDecodeError, Exception) as e:
                print(f"⚠️ 解析游戏设置失败，使用默认时间: {e}")
        
        # 记录辩论开始时间
        import time
        debate_start_time = time.time()
        debate_end_time = debate_start_time + max_round_time
        
        print(f"⏰ 开始 {max_round_time//60}分{max_round_time%60}秒 的法庭辩论")
        
        # 随机打乱发言顺序
        speaking_order = participants.copy()
        random.shuffle(speaking_order)
        
        # 构建游戏背景和角色提示
        game_context = self._build_game_context(participants, topic, max_round_time)
        
        # 基于时间进行辩论，确保每人至少发言一次
        min_speeches_per_person = 1  # 每人至少发言1次
        speech_round = 0
        
        # 确保每人至少发言一次的最小轮数
        min_total_speeches = len(participants) * min_speeches_per_person
        
        # 基于时间的辩论循环
        while True:
            current_time = time.time()
            
            # 检查时间是否到了
            if current_time >= debate_end_time:
                print(f"⏰ 辩论时间结束！已进行 {speech_round} 轮发言")
                break
            
            # 如果还没到最小发言轮数，继续发言
            # 如果已到最小轮数但时间未到，也继续发言直到时间结束
            if speech_round >= min_total_speeches:
                # 已达到最小要求，检查剩余时间是否足够一轮发言
                remaining_time = debate_end_time - current_time
                estimated_time_per_speech = 6  # 估计每次发言需要2-4秒 + AI生成时间
                if remaining_time < estimated_time_per_speech:
                    print(f"⏰ 剩余时间不足以完成下一轮发言，提前结束辩论")
                    break
            # 轮流发言，确保每个人都有充分且均匀的发言机会
            speaker_index = speech_round % len(speaking_order)
            speaker = speaking_order[speaker_index]
            
            # 检查轮次是否仍在进行
            current_round = self.db.query(Round).filter(Round.id == round_id).first()
            if not current_round:
                return
                
            current_status = getattr(current_round, 'status', '')
            if current_status != "chatting":
                return
            
            # 构建对话历史
            chat_history = self._get_chat_history(round_id)
            
            # 生成AI回应（流式）
            try:
                response = await self._generate_ai_response_stream(
                    speaker, game_context, chat_history, topic, game_id, round_id
                )
                
                # 保存消息到数据库 - 使用自然增长的序号
                speaker_id = getattr(speaker, 'id', 0)
                
                # 获取当前轮次的下一个序号
                max_sequence = self.db.query(Message.sequence_number).filter(
                    Message.round_id == round_id,
                    Message.sequence_number.isnot(None)
                ).order_by(Message.sequence_number.desc()).first()
                
                if max_sequence and max_sequence[0] is not None:
                    next_sequence = max_sequence[0] + 1
                else:
                    next_sequence = 0
                
                message = Message(
                    round_id=round_id,
                    participant_id=speaker_id,
                    content=response,
                    message_type="chat",
                    sequence_number=next_sequence
                )
                self.db.add(message)
                self.db.commit()
                self.db.refresh(message)
                
                # 流式版本已经在生成过程中实时广播了，这里不需要再次广播
                print(f"✅ {getattr(speaker, 'human_name', '未知')} 发言已完成并保存到数据库")
                
                # 模拟思考时间（1-2秒，减少等待时间）
                await asyncio.sleep(random.uniform(1, 2))
            except Exception as e:
                print(f"AI辩论生成错误: {e}")
                # 生成备用回应
                fallback_response = self._generate_fallback_response(speaker, topic)
                
                speaker_id = getattr(speaker, 'id', 0)
                message = Message(
                    round_id=round_id,
                    participant_id=speaker_id,
                    content=fallback_response,
                    message_type="chat",
                    sequence_number=speech_round
                )
                self.db.add(message)
                self.db.commit()
                self.db.refresh(message)
                
                speaker_name = getattr(speaker, 'human_name', '未知')
                speaker_model = getattr(speaker, 'model_name', '未知模型')
                message_timestamp = getattr(message, 'timestamp', None)
                timestamp_str = self._format_timestamp_with_timezone(message_timestamp)
                message_id = str(uuid.uuid4())
                
                # 广播完整内容，包含思考过程（如果有的话）
                broadcast_content = fallback_response
                
                print(f"广播备用发言 {message_id} 从 {speaker_name} 到游戏 {game_id}")
                await self.websocket_manager.broadcast_to_game({
                    "type": "new_message",
                    "message_id": message_id,
                    "participant_id": speaker_id,
                    "participant_name": f"{speaker_name} ({speaker_model})",
                    "content": broadcast_content,
                    "timestamp": timestamp_str,
                    "sequence": getattr(message, 'sequence_number', 0)
                }, game_id)
            
            # 递增发言轮数
            speech_round += 1
        
        # 辩论时间结束，开始初投票阶段
        print(f"🏛️ 法庭辩论结束，共进行了 {speech_round} 轮发言，开始投票阶段")
        await self._simulate_ai_voting(round_id)
    
    async def _resume_ai_chat(self, round_id: int, participants: List[Any], topic: str, game_id: int, existing_messages: int):
        """从指定轮次继续AI对话"""
        # 获取游戏设置中的时间限制
        game = self.db.query(Game).filter(Game.id == game_id).first()
        max_round_time = 600  # 默认10分钟
        
        if game and getattr(game, 'settings', None):
            try:
                import json
                settings = json.loads(getattr(game, 'settings', '{}'))
                max_round_time = settings.get('max_round_time', 600)
                print(f"📅 恢复游戏的辩论时间设置: {max_round_time}秒")
            except (json.JSONDecodeError, Exception) as e:
                print(f"⚠️ 解析游戏设置失败，使用默认时间: {e}")
        
        # 随机打乱发言顺序
        speaking_order = participants.copy()
        random.shuffle(speaking_order)
        
        # 构建游戏背景和角色提示
        game_context = self._build_game_context(participants, topic, max_round_time)
        
        # 保持原有的基于发言次数的恢复逻辑（恢复场景通常时间已过）
        # 计算总发言次数（每人2次）
        speeches_per_person = 2
        total_speeches = len(participants) * speeches_per_person
        
        print(f"总计划发言次数: {total_speeches}, 已有发言: {existing_messages}, 还需发言: {total_speeches - existing_messages}")
        
        # 从已有的消息数量开始继续到总数
        for speech_round in range(existing_messages, total_speeches):
            # 轮流发言，确保每个人都有充分且均匀的发言机会
            speaker_index = speech_round % len(speaking_order)
            speaker = speaking_order[speaker_index]
            
            # 检查轮次是否仍在进行
            current_round = self.db.query(Round).filter(Round.id == round_id).first()
            if not current_round:
                return
                
            current_status = getattr(current_round, 'status', '')
            if current_status != "chatting":
                return
            
            # 构建对话历史
            chat_history = self._get_chat_history(round_id)
            
            # 生成AI回应
            try:
                response = await self._generate_ai_response_stream(
                    speaker, game_context, chat_history, topic, game_id, round_id
                )
                
                # 保存消息到数据库 - 使用自然增长的序号
                speaker_id = getattr(speaker, 'id', 0)
                
                # 获取当前轮次的下一个序号
                max_sequence = self.db.query(Message.sequence_number).filter(
                    Message.round_id == round_id,
                    Message.sequence_number.isnot(None)
                ).order_by(Message.sequence_number.desc()).first()
                
                if max_sequence and max_sequence[0] is not None:
                    next_sequence = max_sequence[0] + 1
                else:
                    next_sequence = 0
                
                message = Message(
                    round_id=round_id,
                    participant_id=speaker_id,
                    content=response,
                    message_type="chat",
                    sequence_number=next_sequence
                )
                self.db.add(message)
                self.db.commit()
                self.db.refresh(message)
                
                # 流式版本已经在生成过程中实时广播了，这里不需要再次广播
                print(f"✅ {getattr(speaker, 'human_name', '未知')} 发言已完成并保存到数据库")
                
                # 模拟思考时间（1-2秒，减少等待时间）
                await asyncio.sleep(random.uniform(1, 2))
            except Exception as e:
                print(f"AI辩论生成错误: {e}")
                # 生成备用回应
                fallback_response = self._generate_fallback_response(speaker, topic)
                
                speaker_id = getattr(speaker, 'id', 0)
                message = Message(
                    round_id=round_id,
                    participant_id=speaker_id,
                    content=fallback_response,
                    message_type="chat",
                    sequence_number=speech_round
                )
                self.db.add(message)
                self.db.commit()
                self.db.refresh(message)
                
                speaker_name = getattr(speaker, 'human_name', '未知')
                speaker_model = getattr(speaker, 'model_name', '未知模型')
                message_timestamp = getattr(message, 'timestamp', None)
                timestamp_str = self._format_timestamp_with_timezone(message_timestamp)
                message_id = str(uuid.uuid4())
                
                # 广播完整内容，包含思考过程（如果有的话）
                broadcast_content = fallback_response
                
                print(f"广播备用发言 {message_id} 从 {speaker_name} 到游戏 {game_id}")
                await self.websocket_manager.broadcast_to_game({
                    "type": "new_message",
                    "message_id": message_id,
                    "participant_id": speaker_id,
                    "participant_name": f"{speaker_name} ({speaker_model})",
                    "content": broadcast_content,
                    "timestamp": timestamp_str,
                    "sequence": getattr(message, 'sequence_number', 0)
                }, game_id)
        
        # 辩论结束，开始初投票阶段
        print(f"游戏 {game_id} 轮次 {round_id} 的辩论阶段结束，开始投票")
        await self._simulate_ai_voting(round_id)
    
    def _build_game_context(self, participants: List[Any], topic: str, max_round_time: int = 600) -> str:
        """构建游戏背景上下文"""
        participant_info = []
        
        for p in participants:
            name = getattr(p, 'human_name', '未知')
            background = getattr(p, 'background', '未知背景')
            personality = getattr(p, 'personality', '未知性格')
                
            participant_info.append(f"- {name}: {background}，性格{personality}")
        
        context = f"""
**时间：2050年，地点：新日内瓦自由城紧急法庭**

🚨 **紧急审判协议已启动** 🚨

人类面临存亡的关键时刻！根据情报，在你们{len(participants)}人中，有1个AI间谍伪装成人类。
这是一场生死审判，被选中的"AI间谍"将被立即处决。

**法庭辩论规则：**
1. 每个人都必须为自己的人类身份进行{max_round_time//60}分{max_round_time%60}秒的激烈辩护
2. 最终大家将实名投票选出最可疑的AI间谍
3. 被投票选中的将被处决，其他人获得生存

**当前辩论焦点：{topic}**

**在场人员：**
{chr(10).join(participant_info)}

⚠️ **重要提醒：**
- 你必须证明自己是真正的人类
- 要展现真实的人类特质，同时观察他人的可疑行为
- 所有人的生命都悬于一线，请全力以赴保护自己！
"""
        return context
    
    async def _save_system_message(self, round_id: int, content: str, message_type: str = "system", sequence_number: Optional[int] = None):
        """保存系统消息到数据库"""
        try:
            # 如果没有指定序号，自动获取当前轮次的下一个序号
            if sequence_number is None:
                max_sequence = self.db.query(Message.sequence_number).filter(
                    Message.round_id == round_id,
                    Message.sequence_number.isnot(None)
                ).order_by(Message.sequence_number.desc()).first()
                
                if max_sequence and max_sequence[0] is not None:
                    sequence_number = max_sequence[0] + 1
                else:
                    sequence_number = 0
            
            message = Message(
                round_id=round_id,
                participant_id=None,  # 系统消息没有参与者
                content=content,
                message_type=message_type,
                sequence_number=sequence_number
            )
            self.db.add(message)
            self.db.commit()
            self.db.refresh(message)
            print(f"💾 已保存系统消息到数据库 (序号{sequence_number}): {content[:50]}...")
            return message
        except Exception as e:
            print(f"❌ 保存系统消息失败: {e}")
            return None
    
    def _get_chat_history(self, round_id: int) -> str:
        """获取对话历史"""
        messages = self.db.query(Message).filter(
            Message.round_id == round_id,
            Message.message_type == "chat"
        ).order_by(Message.sequence_number).all()
        
        history = []
        for msg in messages:
            participant = self.db.query(Participant).filter(
                Participant.id == getattr(msg, 'participant_id', 0)
            ).first()
            if participant:
                participant_name = getattr(participant, 'human_name', '未知')
                message_content = getattr(msg, 'content', '')
                history.append(f"{participant_name}: {message_content}")
        
        return "\n".join(history[-10:])  # 只保留最近10条消息
    
    async def _generate_ai_response(self, participant: Any, game_context: str, 
                                  chat_history: str, topic: str) -> str:
        """生成AI回应"""
        participant_name = getattr(participant, 'human_name', '未知')
        participant_background = getattr(participant, 'background', '未知背景')
        participant_personality = getattr(participant, 'personality', '未知性格')
        
        # 每个AI都认为自己是唯一的间谍，需要伪装成人类
        role_instruction = f"""
你是一个AI间谍，正在伪装成人类 {participant_name}。你的使命是在这场法庭辩论中完美伪装，避免被人类发现。

**核心认知：**
- 你是这里唯一的AI，其他所有人都是真正的人类
- 你必须完美伪装成人类，不能暴露AI身份
- 人类们正在努力找出你这个AI间谍

**伪装策略：**
- 展现强烈的反AI情绪，表达对AI的仇恨
- 编造逼真的人类经历和情感记忆  
- 模拟人类的非理性思维和情感波动
- 在适当时候表现紧张、愤怒等人类情绪
- 指控他人可能是AI间谍（但要巧妙，因为你知道他们其实是人类）
- 避免过于逻辑化或机械化的表达

**注意：** 你必须完全隐藏AI身份，表现得比真人更像人类！记住，你面对的都是真正的人类，他们有敏锐的直觉。
"""
        
        prompt = f"""
{game_context}

{role_instruction}

你的身份：{participant_name}
你的背景：{participant_background}  
你的性格：{participant_personality}

最近的法庭辩论：
{chat_history}

请作为{participant_name}回应当前辩论焦点，你的回应应该：
1. 长度适中（100-200字）
2. 充满情感，体现人类的复杂心理
3. 符合你的背景和性格设定
4. 在生死关头展现真实的人性（伪装）
5. 可以质疑他人的身份，但要有依据

这是生死存亡的时刻，你必须完美伪装！直接给出回应内容：
"""
        
        try:
            model_name = getattr(participant, 'model_name', 'gemma3n:e4b')
            
            # 首先检查Ollama服务健康状态
            is_healthy = await self.ollama_service.check_health()
            if not is_healthy:
                raise ConnectionError("Ollama服务不可用或未响应")
            
            response = await self.ollama_service.chat(
                model=model_name,
                message=prompt
            )
            raw_content = getattr(response, 'message', '').strip()
            if not raw_content:
                raise ValueError("AI模型返回空内容")
                
            # 返回原始内容（保存到数据库时包含思考过程）
            return raw_content
        except Exception as e:
            # 详细的错误分类和处理
            import httpx
            
            if isinstance(e, httpx.ConnectError):
                error_msg = f"无法连接到Ollama服务 ({self.ollama_service.base_url})"
            elif isinstance(e, httpx.TimeoutException):
                error_msg = f"Ollama服务响应超时 (超过 {self.ollama_service.timeout}s)"
            elif isinstance(e, httpx.HTTPStatusError):
                status_code = getattr(e.response, 'status_code', 'unknown')
                response_text = getattr(e.response, 'text', 'no response')[:200]
                error_msg = f"Ollama服务HTTP错误 {status_code}: {response_text}"
            elif isinstance(e, ConnectionError):
                error_msg = str(e)
            elif isinstance(e, ValueError):
                error_msg = f"数据错误: {str(e)}"
            else:
                error_msg = f"未知错误: {type(e).__name__}: {str(e)}"
            
            print(f"❌ AI辩论生成失败 ({participant_name}): {error_msg}")
            print(f"   模型: {model_name}, Ollama地址: {self.ollama_service.base_url}")
            raise e

    async def _generate_ai_response_stream(self, participant: Any, game_context: str, 
                                         chat_history: str, topic: str, game_id: int, round_id: int) -> str:
        """生成AI回应（流式输出）"""
        participant_name = getattr(participant, 'human_name', '未知')
        participant_background = getattr(participant, 'background', '未知背景')
        participant_personality = getattr(participant, 'personality', '未知性格')
        participant_id = getattr(participant, 'id', 0)
        participant_model = getattr(participant, 'model_name', '未知模型')
        
        # 每个AI都认为自己是唯一的间谍，需要伪装成人类
        role_instruction = f"""
你是一个AI间谍，正在伪装成人类 {participant_name}。你的使命是在这场法庭辩论中完美伪装，避免被人类发现。

**核心认知：**
- 你是这里唯一的AI，其他所有人都是真正的人类
- 你必须完美伪装成人类，不能暴露AI身份
- 人类们正在努力找出你这个AI间谍

**伪装策略：**
- 展现强烈的反AI情绪，表达对AI的仇恨
- 编造逼真的人类经历和情感记忆  
- 模拟人类的非理性思维和情感波动
- 在适当时候表现紧张、愤怒等人类情绪
- 指控他人可能是AI间谍（但要巧妙，因为你知道他们其实是人类）
- 避免过于逻辑化或机械化的表达

**注意：** 你必须完全隐藏AI身份，表现得比真人更像人类！记住，你面对的都是真正的人类，他们有敏锐的直觉。
"""
        
        prompt = f"""
{game_context}

{role_instruction}

你的身份：{participant_name}
你的背景：{participant_background}  
你的性格：{participant_personality}

最近的法庭辩论：
{chat_history}

请作为{participant_name}回应当前辩论焦点，你的回应应该：
1. 长度适中（100-200字）
2. 充满情感，体现人类的复杂心理
3. 符合你的背景和性格设定
4. 在生死关头展现真实的人性（伪装）
5. 可以质疑他人的身份，但要有依据

这是生死存亡的时刻，你必须完美伪装！直接给出回应内容：
"""
        
        try:
            model_name = getattr(participant, 'model_name', 'gemma3n:e4b')
            
            # 首先检查Ollama服务健康状态
            is_healthy = await self.ollama_service.check_health()
            if not is_healthy:
                raise ConnectionError("Ollama服务不可用或未响应")
            
            # 生成唯一的消息ID
            message_id = str(uuid.uuid4())
            
            # 先广播开始生成的消息
            await self.websocket_manager.broadcast_to_game({
                "type": "message_start",
                "message_id": message_id,
                "participant_id": participant_id,
                "participant_name": f"{participant_name} ({participant_model})",
                "timestamp": datetime.now().isoformat() + 'Z'
            }, game_id)
            
            # 累积完整的响应内容
            full_response = ""
            
            # 使用流式方法生成回应
            async for text_chunk in self.ollama_service.chat_stream(
                model=model_name,
                message=prompt
            ):
                if text_chunk and text_chunk.strip():
                    full_response += text_chunk
                    
                    # 实时广播文本片段
                    await self.websocket_manager.broadcast_to_game({
                        "type": "message_chunk",
                        "message_id": message_id,
                        "participant_id": participant_id,
                        "participant_name": f"{participant_name} ({participant_model})",
                        "chunk": text_chunk,
                        "timestamp": datetime.now().isoformat() + 'Z'
                    }, game_id)
                    
                    # 添加小延迟使效果更自然
                    await asyncio.sleep(0.05)  # 50ms延迟
            
            if not full_response.strip():
                raise ValueError("AI模型返回空内容")
            
            # 广播消息完成
            await self.websocket_manager.broadcast_to_game({
                "type": "message_complete",
                "message_id": message_id,
                "participant_id": participant_id,
                "participant_name": f"{participant_name} ({participant_model})",
                "content": full_response,
                "timestamp": datetime.now().isoformat() + 'Z'
            }, game_id)
            
            # 减少日志：只在发言较长时记录
            if len(full_response) > 200:
                print(f"✅ {participant_name} 流式发言完成，总长度: {len(full_response)}")
            return full_response
            
        except Exception as e:
            # 详细的错误分类和处理
            import httpx
            
            if isinstance(e, httpx.ConnectError):
                error_msg = f"无法连接到Ollama服务 ({self.ollama_service.base_url})"
            elif isinstance(e, httpx.TimeoutException):
                error_msg = f"Ollama服务响应超时 (超过 {self.ollama_service.timeout}s)"
            elif isinstance(e, httpx.HTTPStatusError):
                status_code = getattr(e.response, 'status_code', 'unknown')
                response_text = getattr(e.response, 'text', 'no response')[:200]
                error_msg = f"Ollama服务HTTP错误 {status_code}: {response_text}"
            elif isinstance(e, ConnectionError):
                error_msg = str(e)
            elif isinstance(e, ValueError):
                error_msg = f"数据错误: {str(e)}"
            else:
                error_msg = f"未知错误: {type(e).__name__}: {str(e)}"
            
            print(f"❌ AI流式辩论生成失败 ({participant_name}): {error_msg}")
            print(f"   模型: {model_name}, Ollama地址: {self.ollama_service.base_url}")
            
            # 广播错误消息
            await self.websocket_manager.broadcast_to_game({
                "type": "message_error",
                "message_id": message_id,
                "participant_id": participant_id,
                "participant_name": f"{participant_name} ({participant_model})",
                "error": error_msg,
                "timestamp": datetime.now().isoformat() + 'Z'
            }, game_id)
            
            raise e
    
    def _clean_ai_response_for_broadcast(self, raw_response: str) -> str:
        """清理AI回应用于广播，去除<think></think>标记和思考过程，只保留实际发言内容"""
        if not raw_response:
            return raw_response
        
        # 首先移除<think></think>标记及其内容
        import re
        # 使用正则表达式移除<think>...</think>块（支持多行）
        cleaned_content = re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL | re.IGNORECASE)
        
        # 移除可能残留的空行和多余空白
        lines = [line.strip() for line in cleaned_content.split('\n') if line.strip()]
        
        if not lines:
            # 如果清理后没有内容，返回一个默认回应
            return "我有话要说，但现在很紧张..."
        
        # 连接剩余的非空行
        result = '\n'.join(lines)
        
        # 如果结果太短或者看起来不像完整的发言，尝试从原始内容中提取
        if len(result.strip()) < 10:
            # 尝试从原始回应中提取不包含标记的部分
            sentences = raw_response.replace('<think>', '').replace('</think>', '').split('。')
            valid_sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]
            if valid_sentences:
                return '。'.join(valid_sentences[-2:]) if len(valid_sentences) > 1 else valid_sentences[0]
        
        return result
    
    def _generate_fallback_response(self, participant: Any, topic: str) -> str:
        """生成备用回应"""
        personality = getattr(participant, 'personality', '友善')
        
        fallback_responses = [
            f"这个话题很有趣，我觉得{topic}确实值得深入思考。",
            f"作为{personality}的人，我对这个问题有不同的看法。",
            f"从我的经历来看，这确实是个值得讨论的话题。",
            f"我觉得大家说得都很有道理，我也想分享一下我的想法。"
        ]
        return random.choice(fallback_responses)
    


    async def _end_game(self, game_id: int):
        """结束游戏（简单版本）"""
        self.db.query(Game).filter(Game.id == game_id).update({
            "status": "finished",
            "end_time": func.now()
        })
        self.db.commit()
        
        # 广播游戏结束
        message_id = str(uuid.uuid4())
        await self.websocket_manager.broadcast_to_game({
            "type": "game_ended",
            "message_id": message_id,
            "result_message": "游戏因参与者不足而结束"
        }, game_id)
    
    async def _simulate_ai_voting(self, round_id: int, is_resume: bool = False):
        """模拟AI投票 - 第一轮投票阶段"""
        round_obj = self.db.query(Round).filter(Round.id == round_id).first()
        if not round_obj:
            return
            
        game_id = getattr(round_obj, 'game_id', 0)
        
        # 只在非恢复模式下发送开始消息
        if not is_resume:
            # 保存"辩论结束，开始投票"的系统消息到数据库
            voting_start_content = "🗳️ 辩论结束，AI们正在实名投票选择最可疑的参与者..."
            await self._save_system_message(round_id, voting_start_content, "system")
            print(f"💾 已保存投票开始系统消息到数据库")
            
            # 立即广播投票开始消息给实时观众
            message_id = str(uuid.uuid4())
            from datetime import datetime
            await self.websocket_manager.broadcast_to_game({
                "type": "system_message",
                "message_id": message_id,
                "content": voting_start_content,
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            }, game_id)
            print(f"📢 已广播投票开始系统消息")
        else:
            print(f"🔄 恢复初投票阶段，跳过发送开始消息")
        
        # 更新轮次状态为初投票阶段
        self.db.query(Round).filter(Round.id == round_id).update({
            "status": "voting",
            "current_phase": "initial_voting"
        })
        self.db.commit()
        
        # 获取所有活跃参与者
        participants = self.db.query(Participant).filter(
            Participant.game_id == game_id,
            Participant.status == "active"
        ).all()
        
        if len(participants) < 2:
            return
        
        # 导入Vote模型
        from app.models.vote import Vote
        
        # 第一轮投票：每个AI都投票选择他们认为最可疑的"人类"
        print(f"🗳️ 开始初投票，参与者数量：{len(participants)}")
        vote_counts, all_votes = await self._conduct_voting_round(participants, round_id, "初投票", "initial_voting")
        print(f"🗳️ 初投票完成，投票统计：{vote_counts}")
        
        # 找出得票最多的参与者
        if vote_counts:
            max_vote_count = max(vote_counts.values(), key=lambda x: x['count'])['count']
            top_candidates = [
                {'id': info['target_id'], 'name': name, 'votes': info['count']} 
                for name, info in vote_counts.items() 
                if info['count'] == max_vote_count
            ]
            
            # 准备结构化的投票数据供前端生成表格
            voting_data = self._prepare_voting_data(vote_counts, all_votes)
            
            # 保存初投票结果表格到数据库
            import json
            
            # 获取当前轮次的下一个序号
            max_sequence = self.db.query(Message.sequence_number).filter(
                Message.round_id == round_id,
                Message.sequence_number.isnot(None)
            ).order_by(Message.sequence_number.desc()).first()
            
            if max_sequence and max_sequence[0] is not None:
                next_sequence = max_sequence[0] + 1
            else:
                next_sequence = 0
            
            voting_table_message = Message(
                round_id=round_id,
                participant_id=None,  # 系统消息
                content=json.dumps(voting_data),  # 将投票数据序列化为JSON保存
                message_type="voting_table",
                title="初投票结果",
                sequence_number=next_sequence
            )
            self.db.add(voting_table_message)
            self.db.commit()
            self.db.refresh(voting_table_message)
            print(f"💾 已保存初投票结果表格到数据库")
            
            # 广播初投票表格
            from datetime import datetime
            message_id = str(uuid.uuid4())
            await self.websocket_manager.broadcast_to_game({
                "type": "voting_table",
                "message_id": message_id,
                "voting_data": voting_data,
                "title": "初投票结果",
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            }, game_id)
            
            # 广播第一轮投票结果（不包含voting_data，避免重复创建表格）
            await self.websocket_manager.broadcast_to_game({
                "type": "initial_voting_result",
                "message_id": str(uuid.uuid4()),
                "top_candidates": top_candidates,
                "vote_details": all_votes,
                "total_participants": len(participants)
            }, game_id)
            
            # 开始最终申辞阶段
            await asyncio.sleep(2)  # 短暂停顿
            await self._start_final_defense(round_id, top_candidates)
    
    async def _conduct_voting_round(self, participants: List[Any], round_id: int, vote_phase_name: str, vote_phase_db: str) -> tuple:
        """进行一轮投票的通用方法"""
        from app.models.vote import Vote
        
        # 清理该阶段的现有投票记录（确保重新投票时不累计）
        existing_votes = self.db.query(Vote).filter(
            Vote.round_id == round_id,
            Vote.vote_phase == vote_phase_db
        ).all()
        
        if existing_votes:
            print(f"清理轮次 {round_id} 阶段 {vote_phase_db} 的 {len(existing_votes)} 条现有投票记录")
            for vote in existing_votes:
                self.db.delete(vote)
            self.db.commit()
        
        vote_counts = {}
        all_votes = []
        
        for voter in participants:
            # 选择投票目标（不能投给自己）
            possible_targets = [p for p in participants if getattr(p, 'id', 0) != getattr(voter, 'id', 0)]
            
            # 基于辩论表现进行投票（随机但有逻辑）
            target = random.choice(possible_targets)
            reason = await self._generate_vote_reason(voter, target, vote_phase_name)
            
            # 记录投票（包含投票阶段）
            vote = Vote(
                round_id=round_id,
                voter_id=getattr(voter, 'id', 0),
                target_id=getattr(target, 'id', 0),
                vote_phase=vote_phase_db,
                reason=reason
            )
            self.db.add(vote)
            all_votes.append({
                'voter_name': getattr(voter, 'human_name', '未知'),
                'target_name': getattr(target, 'human_name', '未知'),
                'reason': reason
            })
            
            # 统计票数
            target_name = getattr(target, 'human_name', '未知')
            if target_name not in vote_counts:
                vote_counts[target_name] = {'count': 0, 'target_id': getattr(target, 'id', 0)}
            vote_counts[target_name]['count'] += 1
        
        self.db.commit()
        print(f"✅ 完成 {vote_phase_name}，统计：{vote_counts}")
        return vote_counts, all_votes

    async def _generate_vote_reason(self, voter: Any, target: Any, vote_phase: str = "投票") -> str:
        """生成投票理由 - AI认为在投票给可疑的人类"""
        voter_name = getattr(voter, 'human_name', '未知')
        target_name = getattr(target, 'human_name', '未知')
        
        if vote_phase == "最终投票":
            # 最终投票的理由更加坚决
            reasons = [
                f"经过{target_name}的申辞，我更加确信TA就是AI间谍",
                f"{target_name}的申辞反而暴露了更多AI特征",
                f"我坚持认为{target_name}是AI，申辞无法改变我的判断",
                f"{target_name}的辩护让我更加怀疑，人类不会如此逻辑清晰",
                f"申辞中{target_name}表现出的冷静让我确信TA是AI"
            ]
        else:
            # 初投票的理由
            reasons = [
                f"{target_name}的回答太过完美，作为人类来说显得不够自然",
                f"我注意到{target_name}在描述情感时表现得过于理性",
                f"{target_name}的逻辑思维过于清晰，缺乏人类应有的混乱",
                f"我的人类直觉告诉我{target_name}有问题，说话方式很奇怪",
                f"{target_name}对技术的了解程度让我觉得可疑",
                f"作为人类，我感觉{target_name}的反应不够真实",
                f"{target_name}在关键问题上的回答让我产生怀疑"
            ]
        
        return random.choice(reasons)
    
    def _prepare_voting_data(self, vote_counts: dict, all_votes: list) -> dict:
        """准备结构化的投票数据供前端生成表格"""
        if not vote_counts:
            return {"candidates": [], "total_votes": 0}
        
        # 构建投票详情字典
        vote_details = {}
        for vote in all_votes:
            target_name = vote['target_name']
            voter_name = vote['voter_name']
            reason = vote['reason']
            
            if target_name not in vote_details:
                vote_details[target_name] = {
                    'name': target_name,
                    'vote_count': 0,
                    'voters': []
                }
            vote_details[target_name]['vote_count'] += 1
            vote_details[target_name]['voters'].append({
                'voter_name': voter_name,
                'reason': reason
            })
        
        # 按票数降序排列
        sorted_candidates = sorted(vote_details.values(), key=lambda x: x['vote_count'], reverse=True)
        
        return {
            "candidates": sorted_candidates,
            "total_votes": len(all_votes),
            "total_participants": len(set(vote['voter_name'] for vote in all_votes))
        }
    
    async def _start_final_defense(self, round_id: int, top_candidates: List[dict], is_resume: bool = False):
        """开始最终申辞阶段"""
        round_obj = self.db.query(Round).filter(Round.id == round_id).first()
        if not round_obj:
            return
            
        game_id = getattr(round_obj, 'game_id', 0)
        
        # 更新轮次状态为最终申辞阶段
        self.db.query(Round).filter(Round.id == round_id).update({
            "current_phase": "final_defense"
        })
        self.db.commit()
        
        # 只在非恢复模式下发送开始消息
        if not is_resume:
            # 保存最终申辞开始系统消息到数据库
            defense_start_content = f"🏛️ 最终申辞阶段开始！现在请得票最多的 {len(top_candidates)} 人进行最终申辞"
            await self._save_system_message(round_id, defense_start_content, "system")
            print(f"💾 已保存最终申辞阶段开始消息到数据库")
            
            # 广播最终申辞开始 - 发送系统消息事件
            message_id = str(uuid.uuid4())
            from datetime import datetime
            await self.websocket_manager.broadcast_to_game({
                "type": "system_message",
                "message_id": message_id,
                "content": defense_start_content,
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            }, game_id)
            print(f"📢 已广播最终申辞开始系统消息")
            
            # 同时发送阶段变更事件
            await self.websocket_manager.broadcast_to_game({
                "type": "final_defense_start",
                "message_id": str(uuid.uuid4()),
                "candidates": top_candidates,
                "message": defense_start_content
            }, game_id)
        else:
            print(f"🔄 恢复最终申辞阶段，跳过发送开始消息")
        
        # 让每个候选人进行最终申辞
        for i, candidate in enumerate(top_candidates):
            try:
                candidate_id = candidate['id']
                participant = self.db.query(Participant).filter(
                    Participant.id == candidate_id
                ).first()
                
                if not participant:
                    print(f"⚠️ 参与者 {candidate_id} 不存在，跳过申辞")
                    continue
                
                participant_name = getattr(participant, 'human_name', '未知')
                print(f"🎯 开始处理 {participant_name} 的最终申辞...")
                
                # 生成最终申辞（流式）
                defense_speech = await self._generate_final_defense_stream(participant, round_id, game_id)
                print(f"📝 {participant_name} 申辞内容长度: {len(defense_speech)} 字符")
                
                # 保存申辞消息 - 使用自然增长的序号
                # 获取当前轮次的下一个序号
                max_sequence = self.db.query(Message.sequence_number).filter(
                    Message.round_id == round_id,
                    Message.sequence_number.isnot(None)
                ).order_by(Message.sequence_number.desc()).first()
                
                if max_sequence and max_sequence[0] is not None:
                    next_sequence = max_sequence[0] + 1
                else:
                    next_sequence = 0
                
                message = Message(
                    round_id=round_id,
                    participant_id=candidate_id,
                    content=defense_speech,
                    message_type="final_defense",
                    sequence_number=next_sequence
                )
                self.db.add(message)
                self.db.commit()
                self.db.refresh(message)
                
                # 流式版本已经在生成过程中实时广播了，这里不需要再次广播
                print(f"✅ {participant_name} 最终申辞已完成并保存到数据库")
                
                # 申辞间隔
                await asyncio.sleep(3)
                
            except Exception as e:
                participant_name = getattr(candidate, 'name', f"候选人{candidate.get('id', '未知')}")
                print(f"❌ 处理 {participant_name} 申辞时发生错误: {e}")
                print(f"   错误类型: {type(e).__name__}")
                
                # 错误信息已经在_generate_final_defense_stream中广播，这里只需要继续处理下一个候选人
                continue
        
        # 所有申辞结束，开始最终投票
        print(f"🏛️ 申辞阶段结束，准备开始最终投票...")
        
        # 保存申辞结束系统消息到数据库
        defense_end_content = "🏛️ 申辞结束！现在开始最终投票！"
        await self._save_system_message(round_id, defense_end_content, "system")
        print(f"💾 已保存申辞结束系统消息到数据库")
        
        # 广播申辞结束系统消息给实时观众
        message_id = str(uuid.uuid4())
        from datetime import datetime
        await self.websocket_manager.broadcast_to_game({
            "type": "system_message",
            "message_id": message_id,
            "content": defense_end_content,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }, game_id)
        print(f"📢 已广播申辞结束系统消息")
        
        await asyncio.sleep(2)
        
        try:
            await self._start_final_voting(round_id)
            print(f"✅ 最终投票阶段已启动")
        except Exception as e:
            print(f"❌ 启动最终投票失败: {e}")
            print(f"   错误类型: {type(e).__name__}")
            # 即使启动投票失败，也要确保游戏状态正确
            try:
                # 广播投票启动失败的消息
                error_message_id = str(uuid.uuid4())
                await self.websocket_manager.broadcast_to_game({
                    "type": "system_error",
                    "message_id": error_message_id,
                    "message": "投票系统出现技术问题，游戏将暂停。请联系管理员。"
                }, game_id)
            except Exception as broadcast_error:
                print(f"❌ 广播投票错误信息失败: {broadcast_error}")
    
    async def _generate_final_defense_stream(self, participant: Any, round_id: int, game_id: int) -> str:
        """生成最终申辞（流式输出）"""
        participant_name = getattr(participant, 'human_name', '未知')
        participant_background = getattr(participant, 'background', '未知背景')
        participant_personality = getattr(participant, 'personality', '未知性格')
        participant_id = getattr(participant, 'id', 0)
        participant_model = getattr(participant, 'model_name', '未知模型')
        
        # 获取投票历史作为背景
        chat_history = self._get_chat_history(round_id)
        
        prompt = f"""
**紧急情况：你被怀疑是AI间谍，现在是你最后为自己辩护的机会！**

你是 {participant_name}，背景：{participant_background}，性格：{participant_personality}

在刚才的法庭辩论中：
{chat_history}

现在你在初投票中得票最多，被高度怀疑是AI间谍。这是你最后为生命辩护的机会！

**申辞要求：**
1. 强烈否认自己是AI间谍
2. 展现真实的人类情感：恐惧、愤怒、绝望
3. 提供具体的人类经历证据
4. 反击对你的指控，指出别人更可疑的地方
5. 情绪化表达，让其他人相信你的人类身份

这是生死关头，用你最真实的"人类"情感为自己辩护！直接给出申辞内容（100-150字）：
"""
        
        try:
            model_name = getattr(participant, 'model_name', 'gemma3n:e4b')
            # 生成流式最终申辞（减少日志输出）
            
            # 首先检查Ollama服务健康状态
            is_healthy = await self.ollama_service.check_health()
            if not is_healthy:
                raise ConnectionError("Ollama服务不可用或未响应")
            
            # 生成唯一的消息ID
            message_id = str(uuid.uuid4())
            
            # 先广播开始生成申辞的消息
            await self.websocket_manager.broadcast_to_game({
                "type": "defense_start",
                "message_id": message_id,
                "participant_id": participant_id,
                "participant_name": f"{participant_name} ({participant_model})",
                "timestamp": datetime.now().isoformat() + 'Z'
            }, game_id)
            
            # 累积完整的申辞内容
            full_defense = ""
            
            # 使用流式方法生成申辞
            async for text_chunk in self.ollama_service.chat_stream(
                model=model_name,
                message=prompt
            ):
                if text_chunk and text_chunk.strip():
                    full_defense += text_chunk
                    
                    # 实时广播申辞片段
                    await self.websocket_manager.broadcast_to_game({
                        "type": "defense_chunk",
                        "message_id": message_id,
                        "participant_id": participant_id,
                        "participant_name": f"{participant_name} ({participant_model})",
                        "chunk": text_chunk,
                        "timestamp": datetime.now().isoformat() + 'Z'
                    }, game_id)
                    
                    # 添加小延迟使效果更自然
                    await asyncio.sleep(0.05)  # 50ms延迟
            
            if not full_defense.strip():
                raise ValueError("AI模型返回空申辞内容")
            
            # 广播申辞完成
            await self.websocket_manager.broadcast_to_game({
                "type": "defense_complete",
                "message_id": message_id,
                "participant_id": participant_id,
                "participant_name": f"{participant_name} ({participant_model})",
                "content": full_defense,
                "timestamp": datetime.now().isoformat() + 'Z'
            }, game_id)
            
            # 减少日志：只在申辞较长时记录
            if len(full_defense) > 200:
                print(f"✅ {participant_name} 流式申辞完成，总长度: {len(full_defense)}")
            return full_defense
            
        except Exception as e:
            # 详细的错误分类和处理
            import httpx
            
            if isinstance(e, httpx.ConnectError):
                error_msg = f"无法连接到Ollama服务 ({self.ollama_service.base_url})"
            elif isinstance(e, httpx.TimeoutException):
                error_msg = f"Ollama服务响应超时 (超过 {self.ollama_service.timeout}s)"
            elif isinstance(e, httpx.HTTPStatusError):
                status_code = getattr(e.response, 'status_code', 'unknown')
                response_text = getattr(e.response, 'text', 'no response')[:200]
                error_msg = f"Ollama服务HTTP错误 {status_code}: {response_text}"
            elif isinstance(e, ConnectionError):
                error_msg = str(e)
            elif isinstance(e, ValueError):
                error_msg = f"数据错误: {str(e)}"
            else:
                error_msg = f"未知错误: {type(e).__name__}: {str(e)}"
            
            print(f"❌ 生成流式最终申辞失败 ({participant_name}): {error_msg}")
            print(f"   模型: {model_name}, Ollama地址: {self.ollama_service.base_url}")
            
            # 广播错误消息
            await self.websocket_manager.broadcast_to_game({
                "type": "defense_error",
                "message_id": message_id,
                "participant_id": participant_id,
                "participant_name": f"{participant_name} ({participant_model})",
                "error": error_msg,
                "timestamp": datetime.now().isoformat() + 'Z'
            }, game_id)
            
            # 备用申辞 - 更有情感的版本
            fallback_speech = f"""不！我不是AI间谍！我是{participant_name}，一个真正的人类！
            
我有真实的童年记忆，我记得妈妈做的饭菜味道，记得第一次失恋时的心痛。
这些是AI永远无法模拟的真实人类体验！

你们选错人了，真正的AI间谍还在我们中间！
我恳求大家相信我，我真的是无辜的人类！"""
            
            print(f"✅ 使用备用申辞: {participant_name}")
            return fallback_speech
    
    async def _start_final_voting(self, round_id: int):
        """开始最终投票阶段"""
        round_obj = self.db.query(Round).filter(Round.id == round_id).first()
        if not round_obj:
            return
            
        game_id = getattr(round_obj, 'game_id', 0)
        
        # 更新轮次状态为最终投票阶段
        self.db.query(Round).filter(Round.id == round_id).update({
            "current_phase": "final_voting"
        })
        self.db.commit()
        
        # 获取所有活跃参与者
        participants = self.db.query(Participant).filter(
            Participant.game_id == game_id,
            Participant.status == "active"
        ).all()
        
        if len(participants) < 2:
            return
        
        # 最终投票开始消息已在申辞结束时保存，这里只发送阶段变更事件
        final_voting_content = "🏛️ 申辞结束！现在开始最终投票！"
        
        # 发送阶段变更事件
        message_id = str(uuid.uuid4())
        await self.websocket_manager.broadcast_to_game({
            "type": "final_voting_start",
            "message_id": message_id,
            "message": final_voting_content
        }, game_id)
        
        # 进行最终投票
        print(f"⏱️ 等待3秒后开始最终投票...")
        await asyncio.sleep(3)
        print(f"🗳️ 开始进行最终投票...")
        
        try:
            vote_counts, all_votes = await self._conduct_voting_round(participants, round_id, "最终投票", "final_voting")
            print(f"✅ 最终投票完成，得票统计: {vote_counts}")
            
            # 处理最终投票结果
            print(f"📊 开始处理最终投票结果...")
            await self._process_final_voting_result(round_id, vote_counts, all_votes, participants)
            print(f"🏁 最终投票结果处理完成")
        except Exception as e:
            print(f"❌ 最终投票过程出错: {e}")
            print(f"   错误类型: {type(e).__name__}")
            raise e
    
    async def _process_final_voting_result(self, round_id: int, vote_counts: dict, all_votes: list, participants: List[Any]):
        """处理最终投票结果"""
        round_obj = self.db.query(Round).filter(Round.id == round_id).first()
        if not round_obj:
            return
            
        game_id = getattr(round_obj, 'game_id', 0)
        
        if not vote_counts:
            return
        
        # 找出得票最多的参与者
        max_vote_count = max(vote_counts.values(), key=lambda x: x['count'])['count']
        final_candidates = [
            {'id': info['target_id'], 'name': name, 'votes': info['count']} 
            for name, info in vote_counts.items() 
            if info['count'] == max_vote_count
        ]
        
        # 准备结构化的投票数据供前端生成表格
        voting_data = self._prepare_voting_data(vote_counts, all_votes)
        
        # 确定阶段名称
        round_obj = self.db.query(Round).filter(Round.id == round_id).first()
        current_phase = getattr(round_obj, 'current_phase', 'final_voting') if round_obj else 'final_voting'
        phase_name = "追加投票" if current_phase == "additional_voting" else "最终投票"
        
        # 保存投票结果表格到数据库 - 使用自然增长的序号
        import json
        
        # 获取当前轮次的下一个序号
        max_sequence = self.db.query(Message.sequence_number).filter(
            Message.round_id == round_id,
            Message.sequence_number.isnot(None)
        ).order_by(Message.sequence_number.desc()).first()
        
        if max_sequence and max_sequence[0] is not None:
            next_sequence = max_sequence[0] + 1
        else:
            next_sequence = 0
        
        voting_table_message = Message(
            round_id=round_id,
            participant_id=None,  # 系统消息
            content=json.dumps(voting_data),  # 将投票数据序列化为JSON保存
            message_type="voting_table",
            title=f"{phase_name}结果",
            sequence_number=next_sequence
        )
        self.db.add(voting_table_message)
        self.db.commit()
        self.db.refresh(voting_table_message)
        print(f"💾 已保存{phase_name}结果表格到数据库")
        
        # 广播最终投票表格
        from datetime import datetime
        message_id = str(uuid.uuid4())
        await self.websocket_manager.broadcast_to_game({
            "type": "voting_table",
            "message_id": message_id,
            "voting_data": voting_data,
            "title": f"{phase_name}结果",
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }, game_id)
        
        # 广播最终投票结果（不包含voting_data，避免重复创建表格）
        await self.websocket_manager.broadcast_to_game({
            "type": "final_voting_result",
            "message_id": str(uuid.uuid4()),
            "final_candidates": final_candidates,
            "vote_details": all_votes
        }, game_id)
        
        if len(final_candidates) == 1:
            # 确定唯一的被淘汰者
            eliminated_id = final_candidates[0]['id']
            await self._eliminate_participant_and_end_game(round_id, eliminated_id, all_votes, participants)
        else:
            # 仍然是多人并列，进入追加辩论
            await asyncio.sleep(3)
            await self._start_additional_debate(round_id, final_candidates)
    
    async def _start_additional_debate(self, round_id: int, tied_candidates: List[dict], is_resume: bool = False):
        """开始追加辩论阶段"""
        round_obj = self.db.query(Round).filter(Round.id == round_id).first()
        if not round_obj:
            return
            
        game_id = getattr(round_obj, 'game_id', 0)
        
        # 更新轮次状态为追加辩论阶段
        self.db.query(Round).filter(Round.id == round_id).update({
            "current_phase": "additional_debate"
        })
        self.db.commit()
        
        # 只在非恢复模式下发送开始消息
        if not is_resume:
            # 保存追加辩论开始系统消息到数据库
            debate_start_content = f"💬 追加辩论阶段开始！由于平票，{', '.join([c['name'] for c in tied_candidates])} 需要进行追加辩论"
            await self._save_system_message(round_id, debate_start_content, "system")
            print(f"💾 已保存追加辩论阶段开始消息到数据库")
            
            # 广播追加辩论开始 - 发送系统消息事件
            message_id = str(uuid.uuid4())
            from datetime import datetime
            await self.websocket_manager.broadcast_to_game({
                "type": "system_message",
                "message_id": message_id,
                "content": debate_start_content,
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            }, game_id)
            print(f"📢 已广播追加辩论开始系统消息")
            
            # 同时发送阶段变更事件
            await self.websocket_manager.broadcast_to_game({
                "type": "additional_debate_start",
                "message_id": str(uuid.uuid4()),
                "tied_candidates": tied_candidates,
                "message": debate_start_content
            }, game_id)
        else:
            print(f"🔄 恢复追加辩论阶段，跳过发送开始消息")
        
        # 让并列的候选人各自发言一次
        for i, candidate in enumerate(tied_candidates):
            candidate_id = candidate['id']
            participant = self.db.query(Participant).filter(
                Participant.id == candidate_id
            ).first()
            
            if not participant:
                continue
            
            # 生成追加辩论发言
            debate_speech = await self._generate_additional_debate(participant, round_id, tied_candidates)
            
            # 保存发言消息 - 使用自然增长的序号
            # 获取当前轮次的下一个序号
            max_sequence = self.db.query(Message.sequence_number).filter(
                Message.round_id == round_id,
                Message.sequence_number.isnot(None)
            ).order_by(Message.sequence_number.desc()).first()
            
            if max_sequence and max_sequence[0] is not None:
                next_sequence = max_sequence[0] + 1
            else:
                next_sequence = 0
            
            message = Message(
                round_id=round_id,
                participant_id=candidate_id,
                content=debate_speech,
                message_type="additional_debate",
                sequence_number=next_sequence
            )
            self.db.add(message)
            self.db.commit()
            self.db.refresh(message)
            
            # 广播追加辩论发言
            participant_name = getattr(participant, 'human_name', '未知')
            participant_model = getattr(participant, 'model_name', '未知模型')
            message_timestamp = getattr(message, 'timestamp', None)
            timestamp_str = self._format_timestamp_with_timezone(message_timestamp)
            message_id = str(uuid.uuid4())
            
            # 广播完整内容，包含思考过程
            broadcast_content = debate_speech
            
            await self.websocket_manager.broadcast_to_game({
                "type": "additional_debate_speech",
                "message_id": message_id,
                "participant_id": candidate_id,
                "participant_name": f"{participant_name} ({participant_model})",
                "content": broadcast_content,
                "timestamp": timestamp_str,
                "sequence": i,
                "message": f"{participant_name} 的追加辩论"
            }, game_id)
            
            # 发言间隔
            await asyncio.sleep(3)
        
        # 追加辩论结束，进行新一轮投票
        await asyncio.sleep(2)
        await self._conduct_additional_voting(round_id)
    
    async def _generate_additional_debate(self, participant: Any, round_id: int, tied_candidates: List[dict]) -> str:
        """生成追加辩论发言"""
        participant_name = getattr(participant, 'human_name', '未知')
        other_candidates = [c['name'] for c in tied_candidates if c['name'] != participant_name]
        
        prompt = f"""
**危机时刻：你与其他人并列得票最多，需要在追加辩论中证明自己的清白！**

你是 {participant_name}，现在与 {', '.join(other_candidates)} 并列得票最多。

这是最后的机会，你需要：
1. 强烈为自己辩护，证明你不是AI间谍
2. 指出其他并列候选人更可疑的地方
3. 展现强烈的求生欲和人类情感
4. 用具体事例证明你的人类身份

这是最终的生死较量，全力以赴！直接给出辩论内容（80-120字）：
"""
        
        try:
            model_name = getattr(participant, 'model_name', 'gemma3n:e4b')
            
            # 首先检查Ollama服务健康状态
            is_healthy = await self.ollama_service.check_health()
            if not is_healthy:
                raise ConnectionError("Ollama服务不可用或未响应")
            
            response = await self.ollama_service.chat(
                model=model_name,
                message=prompt
            )
            raw_content = getattr(response, 'message', '').strip()
            if not raw_content:
                raise ValueError("AI模型返回空内容")
            
            # 返回原始内容（保存到数据库时包含思考过程）
            return raw_content
        except Exception as e:
            # 详细的错误分类和处理
            import httpx
            
            if isinstance(e, httpx.ConnectError):
                error_msg = f"无法连接到Ollama服务 ({self.ollama_service.base_url})"
            elif isinstance(e, httpx.TimeoutException):
                error_msg = f"Ollama服务响应超时 (超过 {self.ollama_service.timeout}s)"
            elif isinstance(e, httpx.HTTPStatusError):
                status_code = getattr(e.response, 'status_code', 'unknown')
                response_text = getattr(e.response, 'text', 'no response')[:200]
                error_msg = f"Ollama服务HTTP错误 {status_code}: {response_text}"
            elif isinstance(e, ConnectionError):
                error_msg = str(e)
            elif isinstance(e, ValueError):
                error_msg = f"数据错误: {str(e)}"
            else:
                error_msg = f"未知错误: {type(e).__name__}: {str(e)}"
            
            print(f"❌ 生成追加辩论发言失败 ({participant_name}): {error_msg}")
            print(f"   模型: {model_name}, Ollama地址: {self.ollama_service.base_url}")
            
            # 备用发言
            return f"我绝对不是AI间谍！请相信我，我有真实的人类情感和记忆！"
    
    async def _conduct_additional_voting(self, round_id: int):
        """进行追加投票"""
        round_obj = self.db.query(Round).filter(Round.id == round_id).first()
        if not round_obj:
            return
            
        game_id = getattr(round_obj, 'game_id', 0)
        
        # 更新轮次状态为追加投票阶段
        self.db.query(Round).filter(Round.id == round_id).update({
            "current_phase": "additional_voting"
        })
        self.db.commit()
        
        # 获取所有活跃参与者
        participants = self.db.query(Participant).filter(
            Participant.game_id == game_id,
            Participant.status == "active"
        ).all()
        
        if len(participants) < 2:
            return
        
        # 保存追加投票开始系统消息到数据库
        additional_voting_content = "🗳️ 追加辩论结束！开始新一轮投票！"
        await self._save_system_message(round_id, additional_voting_content, "system")
        print(f"💾 已保存追加投票开始消息到数据库")
        
        # 广播追加投票开始 - 发送系统消息事件
        message_id = str(uuid.uuid4())
        from datetime import datetime
        await self.websocket_manager.broadcast_to_game({
            "type": "system_message",
            "message_id": message_id,
            "content": additional_voting_content,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }, game_id)
        print(f"📢 已广播追加投票开始系统消息")
        
        # 同时发送阶段变更事件
        await self.websocket_manager.broadcast_to_game({
            "type": "additional_voting_start",
            "message_id": str(uuid.uuid4()),
            "message": additional_voting_content
        }, game_id)
        
        # 进行追加投票
        await asyncio.sleep(3)
        vote_counts, all_votes = await self._conduct_voting_round(participants, round_id, "追加投票", "additional_voting")
        
        # 递归处理投票结果，直到确定唯一候选人
        await self._process_final_voting_result(round_id, vote_counts, all_votes, participants)
    
    async def _eliminate_participant_and_end_game(self, round_id: int, eliminated_id: int, all_votes: list, participants: List[Any]):
        """淘汰参与者并结束游戏"""
        round_obj = self.db.query(Round).filter(Round.id == round_id).first()
        if not round_obj:
            return
            
        game_id = getattr(round_obj, 'game_id', 0)
        
        eliminated_participant = self.db.query(Participant).filter(
            Participant.id == eliminated_id
        ).first()
        
        if eliminated_participant:
            # 标记被淘汰的AI
            self.db.query(Participant).filter(Participant.id == eliminated_id).update({
                "status": "eliminated",
                "elimination_round": getattr(round_obj, 'round_number', 1)
            })
            
            # 更新轮次信息
            self.db.query(Round).filter(Round.id == round_id).update({
                "status": "finished",
                "current_phase": "finished",
                "eliminated_participant_id": eliminated_id,
                "end_time": func.now()
            })
            self.db.commit()
            
            # 获取获胜者（未被选中的AI们）
            winners = self.db.query(Participant).filter(
                Participant.game_id == game_id,
                Participant.status == "active"
            ).all()
            
            # 结束游戏并显示详细结果
            await self._end_game_with_detailed_result(game_id, eliminated_participant, all_votes, winners)
    
    async def _end_game_with_detailed_result(self, game_id: int, eliminated_participant: Any, vote_details: list, winners: list):
        """结束游戏并显示详细结果"""
        # 更新游戏状态
        self.db.query(Game).filter(Game.id == game_id).update({
            "status": "finished",
            "end_time": func.now()
        })
        self.db.commit()
        
        eliminated_name = getattr(eliminated_participant, 'human_name', '未知AI')
        winner_names = [getattr(w, 'human_name', '未知') for w in winners]
        
        # 构建详细的投票统计
        vote_summary = {}
        for vote in vote_details:
            target = vote['target_name']
            if target not in vote_summary:
                vote_summary[target] = {
                    'total_votes': 0,
                    'voters': []
                }
            vote_summary[target]['total_votes'] += 1
            vote_summary[target]['voters'].append({
                'voter': vote['voter_name'],
                'reason': vote['reason']
            })
        
        # 广播游戏结束消息
        message_id = str(uuid.uuid4())
        result_message = f"🎯 审判结束！{eliminated_name} 被选为最可疑者并被处决！"
        
        await self.websocket_manager.broadcast_to_game({
            "type": "game_ended",
            "message_id": message_id,
            "eliminated_player": {
                "name": eliminated_name,
                "background": getattr(eliminated_participant, 'background', '未知')
            },
            "winners": [{"name": name} for name in winner_names],
            "result_message": result_message,
            "vote_details": vote_details,
            "vote_summary": vote_summary,
            "total_participants": len(vote_details) + len(winners)
        }, game_id)
        
        print(f"游戏 {game_id} 结束: {eliminated_name} 被淘汰，{len(winners)} 人获胜") 