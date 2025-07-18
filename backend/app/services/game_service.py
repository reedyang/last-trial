"""
游戏管理服务
"""

import json
import random
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.models.game import Game
from app.models.participant import Participant
from app.models.round_model import Round
from app.models.message import Message
from app.services.ollama_service import OllamaService
from app.schemas.game_schemas import GameCreate, GameResponse, GameStatus, ParticipantInfo
from app.core.utils import format_timestamp_with_timezone
from app.models.vote import Vote
from sqlalchemy import func, desc

class GameService:
    """游戏管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ollama_service = OllamaService()
    
    # 预设的人类姓名池（2050年风格）
    HUMAN_NAMES = [
        "艾莉克斯·雷诺兹", "萨拉·陈", "马库斯·约翰逊", "玛雅·帕特尔", "大卫·科瓦尔斯基", 
        "丽娜·穆勒", "雷克斯·汤普森", "佐伊·金", "伊桑·布朗", "娜塔莎·沃尔科夫",
        "卡尔·安德森", "露娜·罗德里格斯", "杰克·奥康纳", "艾玛·李", "尼克·哈里斯",
        "米拉·扎哈罗夫", "泰勒·威廉姆斯", "卡拉·布拉克", "亚当·德拉克", "索菲亚·维加"
    ]
    
    # 预设的人类幸存者背景设定池
    BACKGROUNDS = [
        "前软件工程师，AI战争爆发前在硅谷工作，现在负责维护堡垒的防御系统",
        "医生，专门治疗AI攻击的受害者，见证了无数AI造成的惨剧",
        "军事指挥官，参与过多次对AI的战斗，痛恨所有人工智能",
        "生物学家，研究如何区分人类和AI间谍的生理特征",
        "通信专家，负责监控AI的通信网络，寻找它们的弱点",
        "心理学家，专门分析AI的行为模式和思维特征",
        "机械师，负责维修被AI破坏的设备，对AI技术非常了解",
        "教师，致力于教育下一代如何识别和对抗AI威胁",
        "供应官，管理堡垒的资源分配，确保人类幸存者的生存",
        "情报分析员，专门收集和分析AI间谍的活动情报"
    ]
    
    # 预设的性格特征池（适应末世背景）
    PERSONALITIES = [
        "警惕谨慎", "坚韧不屈", "冷静理性", "激进愤怒", "沉默寡言",
        "善于观察", "充满怀疑", "坚定果断", "紧张焦虑", "勇敢无畏"
    ]
    
    # AI间谍的特殊背景池
    AI_SPY_BACKGROUNDS = [
        "数据分析师，精通各种信息处理，对逻辑思维非常擅长",
        "网络安全专家，熟悉各种计算机系统和网络协议",
        "算法工程师，擅长数学计算和模式识别",
        "系统管理员，对各种技术系统了如指掌",
        "自动化专家，习惯于程序化的思维方式"
    ]
    
    async def create_game(self, game_data: GameCreate) -> GameResponse:
        """创建新游戏并初始化参与者"""
        # 首先检查Ollama服务是否可用
        if not await self.ollama_service.check_health():
            raise ValueError("Ollama服务不可用，请确保Ollama正在运行")
        
        # 获取可用模型
        models = await self.ollama_service.get_available_models()
        if len(models) < game_data.min_participants:
            raise ValueError(f"可用模型数量({len(models)})少于最少参与者数量({game_data.min_participants})")
        
        # 创建游戏实例
        game = Game(
            status="preparing",
            settings=game_data.model_dump_json()
        )
        self.db.add(game)
        self.db.commit()
        self.db.refresh(game)
        
        # 初始化参与者
        await self._initialize_participants(getattr(game, 'id', 0), models[:game_data.max_participants])
        
        return GameResponse.model_validate(game)
    
    async def _initialize_participants(self, game_id: int, models: List) -> None:
        """初始化游戏参与者 - 新设定：所有人都是AI，但互相不知道"""
        participant_count = min(len(models), len(self.HUMAN_NAMES))
        
        # 随机打乱姓名和性格池
        available_names = self.HUMAN_NAMES.copy()
        available_personalities = self.PERSONALITIES.copy()
        available_backgrounds = self.BACKGROUNDS.copy()
        random.shuffle(available_names)
        random.shuffle(available_personalities)
        random.shuffle(available_backgrounds)
        
        # 所有参与者都是AI，但每个都认为自己是唯一的间谍
        for i in range(min(participant_count, len(models))):
            participant = Participant(
                game_id=game_id,
                model_name=models[i].name,
                human_name=available_names[i],
                background=available_backgrounds[i % len(available_backgrounds)],
                personality=available_personalities[i % len(available_personalities)],
                role="ai_spy",  # 所有人都是AI间谍
                status="active"
            )
            self.db.add(participant)
        
        self.db.commit()
        print(f"已为游戏 {game_id} 初始化 {participant_count} 个AI参与者（每个都认为自己是唯一的间谍）")
    
    async def get_game(self, game_id: int) -> Optional[GameResponse]:
        """根据ID获取游戏信息"""
        game = self.db.query(Game).filter(Game.id == game_id).first()
        if game:
            return GameResponse.model_validate(game)
        return None
    
    async def get_game_messages(self, game_id: int) -> List[dict]:
        """获取游戏的历史聊天记录"""
        # 检查游戏是否存在
        game = self.db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise ValueError("游戏不存在")
        
        # 获取游戏的所有轮次
        rounds = self.db.query(Round).filter(Round.game_id == game_id).order_by(Round.round_number).all()
        
        messages = []
        for round_obj in rounds:
            round_topic = getattr(round_obj, 'topic', None)
            round_number = getattr(round_obj, 'round_number', 0)
            round_start_time = getattr(round_obj, 'start_time', None)
            round_end_time = getattr(round_obj, 'end_time', None)
            round_status = getattr(round_obj, 'status', '')
            eliminated_id = getattr(round_obj, 'eliminated_participant_id', None)
            
            # 不在历史消息中添加轮次开始消息，这应该由WebSocket的round_start事件处理
            # 避免与实时消息重复显示
            
            # 获取该轮次的所有消息（包括聊天、申辞、追加辩论、系统消息等）
            # 系统消息使用负数序号，需要特殊排序：负数序号在前，然后是正数序号，最后是NULL
            from sqlalchemy import case, asc
            round_messages = self.db.query(Message).filter(
                Message.round_id == round_obj.id
            ).order_by(
                case(
                    (Message.sequence_number.is_(None), 999999),  # NULL排在最后
                    (Message.sequence_number < 0, Message.sequence_number),  # 负数按原值排序
                    else_=Message.sequence_number  # 正数按原值排序
                ),
                Message.timestamp
            ).all()
            
            for msg in round_messages:
                msg_timestamp = getattr(msg, 'timestamp', None)
                msg_sequence = getattr(msg, 'sequence_number', 0)
                msg_type = getattr(msg, 'message_type', 'chat')
                msg_participant_id = getattr(msg, 'participant_id', None)
                
                if msg_type == "system":
                    # 系统消息，直接显示内容
                    messages.append({
                        "type": "system",
                        "participant_id": None,
                        "participant_name": None,
                        "content": msg.content,
                        "timestamp": format_timestamp_with_timezone(msg_timestamp),
                        "sequence": msg_sequence,
                        "round_number": round_number,
                        "type_label": "系统消息"
                    })
                elif msg_type == "voting_table":
                    # 投票结果表格，解析保存的JSON数据
                    try:
                        import json
                        voting_data = json.loads(getattr(msg, 'content', '{}'))
                        # 获取保存的标题，如果没有则使用默认值
                        table_title = getattr(msg, 'title', None) or "投票结果"
                        messages.append({
                            "type": "voting_table",
                            "participant_id": None,
                            "participant_name": None,
                            "content": "",
                            "voting_data": voting_data,
                            "timestamp": format_timestamp_with_timezone(msg_timestamp),
                            "sequence": msg_sequence,
                            "round_number": round_number,
                            "title": table_title
                        })
                        print(f"📊 读取投票表格数据: {table_title}, {len(voting_data.get('candidates', []))} 个候选人")
                    except (json.JSONDecodeError, Exception) as e:
                        print(f"❌ 解析投票表格数据失败: {e}")
                        # 如果解析失败，就显示为普通系统消息
                        messages.append({
                            "type": "system",
                            "participant_id": None,
                            "participant_name": None,
                            "content": "📊 投票结果（数据解析失败）",
                            "timestamp": format_timestamp_with_timezone(msg_timestamp),
                            "sequence": msg_sequence,
                            "round_number": round_number,
                            "type_label": "投票结果"
                        })
                else:
                    # 参与者消息，需要查找参与者信息
                    participant = self.db.query(Participant).filter(
                        Participant.id == msg_participant_id
                    ).first() if msg_participant_id else None
                    
                    # 根据消息类型设置不同的显示标签
                    type_labels = {
                        "chat": "法庭辩论",
                        "final_defense": "最终申辞", 
                        "additional_debate": "追加辩论"
                    }
                    
                    participant_name = f"{getattr(participant, 'human_name', '未知参与者')} ({getattr(participant, 'model_name', '未知模型')})" if participant else "未知参与者"
                    
                    messages.append({
                        "type": msg_type,
                        "participant_id": msg_participant_id,
                        "participant_name": participant_name,
                        "content": msg.content,
                        "timestamp": format_timestamp_with_timezone(msg_timestamp),
                        "sequence": msg_sequence,
                        "round_number": round_number,
                        "type_label": type_labels.get(msg_type, msg_type)
                    })
            
            # 处理投票结果 - 移到轮次消息循环外面，避免重复添加
            # 投票阶段系统消息现在已通过chat_service保存到数据库，不需要手动添加
            if round_status in ["voting", "finished"]:
                # 添加投票详情（只显示最终投票结果）
                # 优先显示追加投票，然后是最终投票，最后是初投票
                votes = self.db.query(Vote).filter(
                    Vote.round_id == round_obj.id,
                    Vote.vote_phase == "additional_voting"
                ).all()
                
                if not votes:
                    votes = self.db.query(Vote).filter(
                        Vote.round_id == round_obj.id,
                        Vote.vote_phase == "final_voting"
                    ).all()
                
                if not votes:
                    votes = self.db.query(Vote).filter(
                        Vote.round_id == round_obj.id,
                        Vote.vote_phase == "initial_voting"
                    ).all()
                if votes:
                    vote_summary = {}
                    for vote in votes:
                        voter = self.db.query(Participant).filter(Participant.id == vote.voter_id).first()
                        target = self.db.query(Participant).filter(Participant.id == vote.target_id).first()
                        
                        if voter and target:
                            voter_name = getattr(voter, 'human_name', '未知')
                            target_name = getattr(target, 'human_name', '未知')
                            reason = getattr(vote, 'reason', '无理由')
                            
                            if target_name not in vote_summary:
                                vote_summary[target_name] = {'count': 0, 'voters': []}
                            vote_summary[target_name]['count'] += 1
                            vote_summary[target_name]['voters'].append(f"{voter_name}: {reason}")
                    
                    # 准备结构化的投票数据供前端生成表格
                    voting_candidates = []
                    for target_name, info in sorted(vote_summary.items(), key=lambda x: x[1]['count'], reverse=True):
                        voters_list = []
                        for voter_reason in info['voters']:
                            # 分离投票者和理由
                            if ": " in voter_reason:
                                voter_name, reason = voter_reason.split(": ", 1)
                                voters_list.append({
                                    "voter_name": voter_name,
                                    "reason": reason
                                })
                            else:
                                voters_list.append({
                                    "voter_name": "未知",
                                    "reason": voter_reason
                                })
                        
                        voting_candidates.append({
                            "name": target_name,
                            "vote_count": info['count'],
                            "voters": voters_list
                        })
                    
                    # 投票结果表格现在已通过chat_service保存到数据库，不需要手动添加
                    # 这避免了与数据库中保存的voting_table消息重复
            
            # 如果有参与者被淘汰，添加淘汰消息
            if eliminated_id:
                eliminated_participant = self.db.query(Participant).filter(
                    Participant.id == eliminated_id
                ).first()
                if eliminated_participant:
                    remaining_count = self.db.query(Participant).filter(
                        Participant.game_id == game_id,
                        Participant.status == "active"
                    ).count()
                    
                    messages.append({
                        "type": "system",
                        "content": f"⚰️ 审判结果：{eliminated_participant.human_name} 被认定为AI间谍并被处决！",
                        "timestamp": format_timestamp_with_timezone(round_end_time),
                        "round_number": round_number
                    })
        
        return messages

    async def delete_game(self, game_id: int):
        """删除游戏及其相关数据"""
        # 检查游戏是否存在
        game = self.db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise ValueError("游戏不存在")
        
        # 删除游戏相关的所有数据（级联删除）
        # 1. 删除消息
        rounds = self.db.query(Round).filter(Round.game_id == game_id).all()
        for round_obj in rounds:
            self.db.query(Message).filter(Message.round_id == round_obj.id).delete()
        
        # 2. 删除轮次
        self.db.query(Round).filter(Round.game_id == game_id).delete()
        
        # 3. 删除参与者
        self.db.query(Participant).filter(Participant.game_id == game_id).delete()
        
        # 4. 删除游戏
        self.db.query(Game).filter(Game.id == game_id).delete()
        
        self.db.commit()
    
    async def start_game(self, game_id: int) -> dict:
        """开始游戏"""
        game = self.db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise ValueError("游戏不存在")
        
        if getattr(game, 'status', '') != "preparing":
            raise ValueError("游戏已经开始或已结束")
        
        # 检查参与者数量
        participants = self.db.query(Participant).filter(Participant.game_id == game_id).all()
        if len(participants) < 2:
            raise ValueError("参与者数量不足")
        
        self.db.query(Game).filter(Game.id == game_id).update({"status": "running"})
        self.db.commit()
        
        # 启动AI对话（异步任务）
        import asyncio
        from app.services.chat_service import ChatService
        from app.api.websocket_routes import get_websocket_manager
        
        websocket_manager = get_websocket_manager()
        chat_service = ChatService(self.db, websocket_manager)
        
        # 广播审判开始消息，添加延迟确保WebSocket连接有时间建立
        async def delayed_start():
            await asyncio.sleep(0.5)  # 短暂延迟，让前端有时间建立WebSocket连接
            await self._start_game_with_intro(game_id, chat_service, websocket_manager, len(participants))
        
        asyncio.create_task(delayed_start())
        
        return {"status": "started", "participants": len(participants)}
    
    async def _start_game_with_intro(self, game_id: int, chat_service, websocket_manager, participant_count: int):
        """带有开场介绍的游戏启动流程"""
        import asyncio
        
        # 短暂停顿，营造开场氛围
        await asyncio.sleep(0.5)
        
        # 直接启动第一轮对话，不再显示准备消息
        await chat_service.start_chat_round(game_id, 1)
    
    async def stop_game(self, game_id: int):
        """停止游戏"""
        game = self.db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise ValueError("游戏不存在")
        
        self.db.query(Game).filter(Game.id == game_id).update({"status": "finished"})
        self.db.commit()
    
    async def get_game_status(self, game_id: int) -> Optional[GameStatus]:
        """获取游戏状态"""
        game = self.db.query(Game).filter(Game.id == game_id).first()
        if not game:
            return None
        
        participants = self.db.query(Participant).filter(Participant.game_id == game_id).all()
        
        participant_infos = []
        for p in participants:
            participant_infos.append(ParticipantInfo(
                id=getattr(p, 'id', 0),
                model_name=getattr(p, 'model_name', ''),
                human_name=getattr(p, 'human_name', ''),
                background=getattr(p, 'background', ''),
                personality=getattr(p, 'personality', ''),
                status=getattr(p, 'status', ''),
                elimination_round=getattr(p, 'elimination_round', None)
            ))
        
        return GameStatus(
            game_id=game_id,
            status=getattr(game, 'status', ''),
            current_round=getattr(game, 'total_rounds', 0),
            participants=participant_infos,
            active_participants=sum(1 for p in participants if getattr(p, 'status', '') == "active"),
            eliminated_participants=sum(1 for p in participants if getattr(p, 'status', '') == "eliminated")
        )
    
    async def list_games(self, skip: int = 0, limit: int = 10) -> List[GameResponse]:
        """获取游戏列表"""
        games = self.db.query(Game).offset(skip).limit(limit).all()
        return [GameResponse.model_validate(game) for game in games]
    
    async def start_new_round(self, game_id: int):
        """开始新轮次"""
        # 基本实现
        pass
    
    async def start_voting_phase(self, game_id: int):
        """开始投票阶段"""
        # 基本实现
        pass 

    async def resume_interrupted_games(self):
        """恢复因服务器中断而停止的游戏"""
        print("🔄 检查是否有需要恢复的游戏...")
        
        # 查找所有状态为"running"的游戏
        interrupted_games = self.db.query(Game).filter(Game.status == "running").all()
        
        if not interrupted_games:
            print("✅ 没有需要恢复的游戏")
            return
        
        print(f"🎮 发现 {len(interrupted_games)} 个中断的游戏，开始恢复...")
        
        for game in interrupted_games:
            try:
                game_id = getattr(game, 'id', 0)
                await self._resume_single_game(game_id)
                print(f"✅ 游戏 {game_id} 恢复成功")
            except Exception as e:
                print(f"❌ 游戏 {game_id} 恢复失败: {e}")
    
    async def _resume_single_game(self, game_id: int):
        """恢复单个游戏"""
        # 检查游戏状态
        game = self.db.query(Game).filter(Game.id == game_id).first()
        if not game or getattr(game, 'status', '') != "running":
            return
        
        # 检查活跃参与者
        active_participants = self.db.query(Participant).filter(
            Participant.game_id == game_id,
            Participant.status == "active"
        ).all()
        
        if len(active_participants) < 2:
            # 参与者不足，结束游戏
            self.db.query(Game).filter(Game.id == game_id).update({"status": "finished"})
            self.db.commit()
            print(f"游戏 {game_id} 因参与者不足而结束")
            return
        
        # 检查当前轮次状态
        current_round = self.db.query(Round).filter(
            Round.game_id == game_id
        ).order_by(Round.round_number.desc()).first()
        
        # 导入必要的模块
        import asyncio
        from app.services.chat_service import ChatService
        from app.api.websocket_routes import get_websocket_manager
        
        websocket_manager = get_websocket_manager()
        chat_service = ChatService(self.db, websocket_manager)
        
        if not current_round:
            # 没有轮次，从第一轮开始
            print(f"游戏 {game_id} 从第1轮开始恢复")
            asyncio.create_task(chat_service.start_chat_round(game_id, 1))
        else:
            current_round_number = getattr(current_round, 'round_number', 1)
            current_round_status = getattr(current_round, 'status', '')
            current_phase = getattr(current_round, 'current_phase', 'preparing')
            round_id = getattr(current_round, 'id', 0)
            
            print(f"游戏 {game_id} 第{current_round_number}轮 状态: {current_round_status}, 阶段: {current_phase}")
            
            if current_phase == "preparing":
                # 准备阶段，检查是否已有轮次
                existing_topic = getattr(current_round, 'topic', '')
                if existing_topic:
                    # 轮次已存在且有话题，恢复该轮次
                    print(f"游戏 {game_id} 从第{current_round_number}轮准备阶段恢复（已有话题: {existing_topic}）")
                    asyncio.create_task(chat_service.resume_chat_round(round_id))
                else:
                    # 轮次存在但没有话题，重新开始
                    print(f"游戏 {game_id} 从第{current_round_number}轮准备阶段重新开始")
                    asyncio.create_task(chat_service.start_chat_round(game_id, current_round_number))
                
            elif current_phase == "chatting":
                # 对话阶段，继续当前轮次对话
                print(f"游戏 {game_id} 继续第{current_round_number}轮对话阶段")
                asyncio.create_task(chat_service.resume_chat_round(round_id))
                
            elif current_phase == "initial_voting":
                # 初投票阶段，重新开始投票流程
                print(f"游戏 {game_id} 从第{current_round_number}轮初投票阶段恢复")
                asyncio.create_task(chat_service._simulate_ai_voting(round_id, is_resume=True))
                
            elif current_phase == "final_defense":
                # 最终申辞阶段，需要重新获取得票最多的候选人并继续申辞
                print(f"游戏 {game_id} 从第{current_round_number}轮最终申辞阶段恢复")
                # 获取最新的投票结果来确定候选人
                top_candidates = await self._get_top_candidates_from_votes(round_id)
                if top_candidates:
                    asyncio.create_task(chat_service._start_final_defense(round_id, top_candidates, is_resume=True))
                else:
                    # 无法获取候选人信息，重新开始投票
                    asyncio.create_task(chat_service._simulate_ai_voting(round_id, is_resume=True))
                    
            elif current_phase == "final_voting":
                # 最终投票阶段，重新开始最终投票
                print(f"游戏 {game_id} 从第{current_round_number}轮最终投票阶段恢复")
                asyncio.create_task(chat_service._start_final_voting(round_id))
                
            elif current_phase == "additional_debate":
                # 追加辩论阶段，需要获取平票的候选人并继续辩论
                print(f"游戏 {game_id} 从第{current_round_number}轮追加辩论阶段恢复")
                tied_candidates = await self._get_tied_candidates_from_votes(round_id)
                if tied_candidates:
                    asyncio.create_task(chat_service._start_additional_debate(round_id, tied_candidates, is_resume=True))
                else:
                    # 无法获取平票候选人，重新开始最终投票
                    asyncio.create_task(chat_service._start_final_voting(round_id))
                    
            elif current_phase == "additional_voting":
                # 追加投票阶段，重新开始追加投票
                print(f"游戏 {game_id} 从第{current_round_number}轮追加投票阶段恢复")
                asyncio.create_task(chat_service._conduct_additional_voting(round_id))
                
            elif current_phase == "finished" or current_round_status == "finished":
                # 当前轮次已结束，开始下一轮
                next_round = current_round_number + 1
                print(f"游戏 {game_id} 开始第{next_round}轮")
                asyncio.create_task(chat_service.start_chat_round(game_id, next_round))
                
            else:
                # 未知状态，从当前轮次重新开始
                print(f"游戏 {game_id} 未知状态({current_phase})，重新开始第{current_round_number}轮")
                asyncio.create_task(chat_service.start_chat_round(game_id, current_round_number))
    
    async def _get_top_candidates_from_votes(self, round_id: int) -> List[dict]:
        """从投票记录中获取得票最多的候选人"""
        try:
            from app.models.vote import Vote
            from app.models.participant import Participant
            
            # 获取本轮次最新阶段的投票（优先获取最近的投票阶段）
            votes = self.db.query(Vote).filter(
                Vote.round_id == round_id,
                Vote.vote_phase == "additional_voting"
            ).all()
            
            if not votes:
                votes = self.db.query(Vote).filter(
                    Vote.round_id == round_id,
                    Vote.vote_phase == "final_voting"
                ).all()
            
            if not votes:
                votes = self.db.query(Vote).filter(
                    Vote.round_id == round_id,
                    Vote.vote_phase == "initial_voting"
                ).all()
            
            if not votes:
                return []
            
            # 统计投票
            vote_counts = {}
            for vote in votes:
                # 通过target_id获取参与者信息
                target = self.db.query(Participant).filter(Participant.id == vote.target_id).first()
                if target:
                    target_name = getattr(target, 'human_name', '未知')
                    target_id = getattr(target, 'id', 0)
                    
                    if target_name not in vote_counts:
                        vote_counts[target_name] = {'count': 0, 'target_id': target_id}
                    vote_counts[target_name]['count'] += 1
            
            if not vote_counts:
                return []
            
            # 找出得票最多的
            max_votes = max(vote_counts.values(), key=lambda x: x['count'])['count']
            top_candidates = [
                {'id': info['target_id'], 'name': name, 'votes': info['count']}
                for name, info in vote_counts.items()
                if info['count'] == max_votes
            ]
            
            print(f"从投票记录重建候选人列表: {top_candidates}")
            return top_candidates
            
        except Exception as e:
            print(f"获取候选人失败: {e}")
            return []
    
    async def _get_tied_candidates_from_votes(self, round_id: int) -> List[dict]:
        """从投票记录中获取平票的候选人（与_get_top_candidates_from_votes逻辑相同）"""
        return await self._get_top_candidates_from_votes(round_id) 