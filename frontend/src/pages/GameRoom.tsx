import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Button,
  Card,
  CardContent,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Avatar,
  CircularProgress,
  Alert
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  Person as PersonIcon
} from '@mui/icons-material';
import { gameService } from '../services/gameService';
import VotingResultTable from '../components/VotingResultTable';

interface GameData {
  id: number;
  status: string;
  start_time: string;
  end_time?: string;
  total_rounds: number;
  winner_count: number;
}

interface GameStatus {
  game_id: number;
  status: string;
  current_round: number;
  participants: any[];
  active_participants: number;
  eliminated_participants: number;
}

interface ChatMessage {
  type: string;
  content?: string;
  participant_id?: number;
  participant_name?: string;
  timestamp?: string;
  sequence?: number;
  round_number?: number;
  topic?: string;
  eliminated_player?: any;
  remaining_players?: number;
  winners?: any[];
  vote_details?: any[];
  humans_won?: boolean;
  ai_spy?: any;
  result_message?: string; // Added for game_ended message
  message?: string; // For WebSocket messages
  voting_data?: {
    candidates: Array<{
      name: string;
      vote_count: number;
      voters: Array<{
        voter_name: string;
        reason: string;
      }>;
    }>;
    total_votes: number;
    total_participants: number;
  };
  title?: string; // For voting table title
  vote_summary?: any; // Added for vote_summary
  // 流式消息支持
  message_id?: string; // 消息唯一标识
  chunk?: string; // 文本片段
  isStreaming?: boolean; // 是否正在流式显示
  streamingContent?: string; // 当前累积的流式内容
  error?: string; // 错误信息
}

const GameRoom: React.FC = () => {
  const { gameId } = useParams<{ gameId: string }>();
  const navigate = useNavigate();
  
  const [game, setGame] = useState<GameData | null>(null);
  const [gameStatus, setGameStatus] = useState<GameStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentTopic, setCurrentTopic] = useState<string>('');
  const [gamePhase, setGamePhase] = useState<string>(''); 
  const [processedMessageIds, setProcessedMessageIds] = useState<Set<string>>(new Set());
  const [processedSystemMessages, setProcessedSystemMessages] = useState<Set<string>>(new Set());
  const [isHistoryMode, setIsHistoryMode] = useState(false);
  const [wsConnectionStatus, setWsConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'reconnecting'>('connecting');
  const [hasShownDisconnectionMessage, setHasShownDisconnectionMessage] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isInitializingRef = useRef(false);

  // 添加打字机光标闪烁动画的CSS样式
  React.useEffect(() => {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0; }
      }
    `;
    document.head.appendChild(style);
    return () => {
      document.head.removeChild(style);
    };
  }, []);


  // 轻量级的游戏状态刷新函数（不重新加载历史消息）
  const refreshGameData = useCallback(async () => {
    if (!gameId) return;

    try {
      const [gameData, statusData] = await Promise.all([
        gameService.getGame(parseInt(gameId)),
        gameService.getGameStatus(parseInt(gameId))
      ]);
      
      setGame(gameData);
      setGameStatus(statusData);
      
      // 根据游戏状态设置gamePhase
      switch (gameData.status) {
        case 'preparing':
          setGamePhase('准备中');
          break;
        case 'running':
          setGamePhase('辩论中');
          break;
        case 'finished':
          setGamePhase('审判结束');
          break;
        default:
          setGamePhase('');
      }
      
      setError(null);
    } catch (err) {
      console.error('刷新游戏数据失败:', err);
    }
  }, [gameId]);

  const loadHistoryMessages = useCallback(async (replaceAll: boolean = false, filterForReconnect: boolean = false) => {
    if (!gameId) return;
    
    try {
      console.log('📚 开始加载历史消息，模式:', { replaceAll, filterForReconnect });
      const historyMessages = await gameService.getGameMessages(parseInt(gameId));
      console.log('📚 获取到历史消息数量:', historyMessages.length);
      
      // 如果是重连场景，需要获取当前游戏状态来过滤消息
      let currentGameStatus = null;
      if (filterForReconnect) {
        try {
          currentGameStatus = await gameService.getGameStatus(parseInt(gameId));
          console.log('🔄 重连时获取到当前游戏状态:', currentGameStatus);
        } catch (err) {
          console.warn('获取游戏状态失败，使用默认过滤:', err);
        }
      }
      
      // 从历史消息中恢复话题信息
      const roundStartMessage = historyMessages.find((msg: any) => msg.type === 'round_start');
      if (roundStartMessage && roundStartMessage.topic) {
        console.log('🔄 从历史消息恢复话题:', roundStartMessage.topic);
        setCurrentTopic(roundStartMessage.topic);
      }
      
      // 过滤历史消息（重连时）
      let filteredMessages = historyMessages;
      if (filterForReconnect && currentGameStatus) {
        const currentRound = currentGameStatus.current_round || 1;
        console.log(`🧹 重连过滤：当前轮次 ${currentRound}，过滤历史消息...`);
        
        filteredMessages = historyMessages.filter((msg: any) => {
          // 保留聊天消息和申辞消息
          if (msg.type === 'chat' || msg.type === 'new_message') {
            return true;
          }
          
          // 保留最终申辞和追加辩论等重要发言
          if (msg.type === 'final_defense' || 
              msg.type === 'final_defense_start' ||
              msg.type === 'final_defense_speech' ||
              msg.type === 'additional_debate' || 
              msg.type === 'additional_debate_start' ||
              msg.type === 'additional_debate_speech') {
            return true;
          }
          
          // 保留投票结果相关消息（重要的游戏结果）
          if (msg.type === 'initial_voting_result' || 
              msg.type === 'final_voting_result' || 
              msg.type === 'voting_result' ||
              msg.type === 'voting_table') {
            console.log('✅ 保留投票结果消息:', msg.type);
            return true;
          }
          
          // 保留最新的轮次开始消息
          if (msg.type === 'round_start') {
            return msg.round_number === currentRound;
          }
          
          // 保留系统连接恢复消息
          if (msg.type === 'system' && msg.content && msg.content.includes('连接已恢复')) {
            return true;
          }
          
          // 过滤掉过时的投票和系统状态消息，但保留重要的审判消息
          if (msg.type === 'system' && msg.content) {
            const content = msg.content;
            
            // 优先保留审判开始、申辞和重要阶段的系统消息
            if (content.includes('申辞') || 
                content.includes('法庭审判开始') ||
                content.includes('法庭审判从中断处恢复') ||
                content.includes('紧急法庭审判开始') ||
                content.includes('继续中断的法庭审判') ||
                content.includes('最终申辞') ||
                content.includes('追加辩论') ||
                content.includes('辩论焦点') ||
                content.includes('审判结束') ||
                content.includes('获胜者') ||
                content.includes('胜利者') ||
                content.includes('AI们正在实名投票')) {
              return true;
            }
            
            // 只过滤掉明确不重要的投票过程消息
            if (content.includes('开始投票') || 
                content.includes('请选择') ||
                content.includes('投票中')) {
              return false;
            }
          }
          
          // 其他消息保留
          return true;
        });
        
        console.log(`📊 过滤结果: ${historyMessages.length} -> ${filteredMessages.length} 条消息`);
      }
      
            // 转换历史消息中的投票结果为表格格式
      // 去重处理：避免同一阶段的投票表格重复
      const votingTableTitles = new Set<string>();
      
      const processedMessages = filteredMessages
        .map((msg: any) => {
          // 转换旧的voting_result消息为voting_table
          if (msg.type === 'voting_result' && msg.voting_data) {
            return {
              ...msg,
              type: 'voting_table',
              title: '投票结果'
            };
          }
          return msg;
        })
        .filter((msg: any) => {
          // 过滤重复的投票表格 - 使用更精确的去重逻辑
          if (msg.type === 'voting_table') {
            // 生成更具体的标识符，包含时间戳和投票数据特征
            const title = msg.title || '投票结果';
            const timestamp = msg.timestamp || '';
            const votingDataHash = msg.voting_data ? 
              `${msg.voting_data.total_votes}_${msg.voting_data.candidates?.length || 0}` : 
              'empty';
            const uniqueId = `${title}_${timestamp.substring(0, 16)}_${votingDataHash}`;
            
            if (votingTableTitles.has(uniqueId)) {
              return false;
            }
            votingTableTitles.add(uniqueId);
          }
          return true;
        });

      // 统计消息类型，用于调试
      const messageTypeCounts: Record<string, number> = {};
      processedMessages.forEach((msg: any) => {
        messageTypeCounts[msg.type] = (messageTypeCounts[msg.type] || 0) + 1;
      });
      console.log('📊 历史消息类型统计:', messageTypeCounts);

      // 为历史消息生成唯一ID并加入已处理集合，防止与WebSocket消息重复
      const messageIds = new Set<string>();
      const systemMessageContents = new Set<string>();
      processedMessages.forEach((msg: any, index: number) => {
        try {
          let messageId;
          
          if (msg.type === 'system') {
            // 系统消息使用基于内容的ID，避免btoa处理中文字符的问题
            const contentHash = msg.content ? 
              `${msg.content.length}_${msg.content.substring(0, 10).replace(/[^a-zA-Z0-9]/g, '')}` : 
              'empty';
            messageId = `system_${contentHash}`;
            // 同时跟踪系统消息内容
            if (msg.content) {
              systemMessageContents.add(msg.content);
            }
          } else {
            // 其他消息使用原有逻辑
            messageId = `history_${gameId}_${msg.round_number || 0}_${msg.sequence || index}_${msg.type}`;
          }
          
          messageIds.add(messageId);
        } catch (msgErr) {
          console.error(`处理第${index}条消息时出错:`, msgErr, '消息内容:', msg);
          // 使用简单的fallback ID
          messageIds.add(`fallback_${index}_${msg.type || 'unknown'}`);
        }
      });
      
      console.log('📚 历史加载完成 - 系统消息数量:', systemMessageContents.size, '总消息数量:', processedMessages.length);
      
      // 详细调试：输出所有消息的基本信息
      if (process.env.NODE_ENV === 'development') {
        console.log('📋 所有加载的消息详情:');
        processedMessages.forEach((msg: any, idx: number) => {
          console.log(`  ${idx}: ${msg.type} | ${msg.participant_name || 'system'} | 内容长度: ${msg.content?.length || 0} | 时间: ${msg.timestamp || 'none'}`);
        });
      }
      
      setProcessedMessageIds(messageIds);
      setProcessedSystemMessages(systemMessageContents);
      
      // 设置消息到界面
      if (replaceAll) {
        // 完全替换消息（用于游戏结束或初始化）
        console.log('📚 完全替换消息列表，新消息数量:', processedMessages.length);
        
        // 按时间戳排序，确保消息按正确顺序显示
        const sortedMessages = processedMessages.sort((a: any, b: any) => {
          const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
          const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
          return timeA - timeB;
        });
        
        // 调试：显示排序后的消息顺序
        if (process.env.NODE_ENV === 'development') {
          console.log('🕒 排序后的消息顺序:');
          sortedMessages.forEach((msg: any, idx: number) => {
            console.log(`  ${idx}: ${msg.type} | ${msg.participant_name || 'system'} | 时间: ${msg.timestamp || 'none'}`);
          });
        }
        
        // 调试：确认最终设置的消息
        if (process.env.NODE_ENV === 'development') {
          console.log('📤 最终设置到界面的消息数量:', sortedMessages.length);
          const finalTypeCounts: Record<string, number> = {};
          sortedMessages.forEach((msg: any) => {
            finalTypeCounts[msg.type] = (finalTypeCounts[msg.type] || 0) + 1;
          });
          console.log('📤 最终消息类型统计:', finalTypeCounts);
        }
        
        setMessages(sortedMessages);
        
        // 延迟滚动到底部，确保DOM更新完成
        setTimeout(() => {
          messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        }, 100);
      } else {
        // 智能合并历史消息和当前消息
        console.log('📚 智能合并消息列表，新消息数量:', processedMessages.length);
        setMessages(prev => {
          // 获取当前消息的时间戳，用于确定插入位置
          const currentMessages = [...prev];
          const newMessages = [...processedMessages];
          
          // 如果没有当前消息，直接使用历史消息
          if (currentMessages.length === 0) {
            console.log('📚 没有当前消息，直接使用历史消息');
            return newMessages;
          }
          
          // 合并逻辑：保留最新的实时消息，补充缺失的历史消息
          const mergedMessages = [...newMessages];
          
          // 添加不在历史消息中的实时消息（比如刚刚的申辞）
          currentMessages.forEach(currentMsg => {
            const isDuplicate = newMessages.some(historyMsg => {
              // 对于系统消息，使用内容和类型来去重
              if (currentMsg.type === 'system' && historyMsg.type === 'system') {
                return historyMsg.content === currentMsg.content;
              }
              
              // 对于投票表消息，使用类型和投票数据来去重
              if (currentMsg.type === 'voting_table' && historyMsg.type === 'voting_table') {
                // 如果两个都有投票数据，比较投票数据的相似性
                if (currentMsg.voting_data && historyMsg.voting_data) {
                  return JSON.stringify(currentMsg.voting_data) === JSON.stringify(historyMsg.voting_data);
                }
                // 如果时间戳相近（5秒内），认为是同一个投票表
                if (currentMsg.timestamp && historyMsg.timestamp) {
                  const timeDiff = Math.abs(new Date(currentMsg.timestamp).getTime() - new Date(historyMsg.timestamp).getTime());
                  return timeDiff < 5000; // 5秒内认为是重复
                }
                return true; // 默认认为是重复
              }
              
              // 对于参与者消息，使用原有逻辑
              return historyMsg.participant_id === currentMsg.participant_id &&
                     historyMsg.timestamp === currentMsg.timestamp &&
                     historyMsg.type === currentMsg.type;
            });
            
            if (!isDuplicate) {
              // 这是一个新的实时消息，需要保留
              console.log('📚 保留实时消息:', currentMsg.type, currentMsg.content?.substring(0, 30));
              mergedMessages.push(currentMsg);
            }
          });
          
          // 按时间戳排序
          const sortedMessages = mergedMessages.sort((a, b) => {
            const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
            const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
            return timeA - timeB;
          });
          
          console.log('📚 合并完成，最终消息数量:', sortedMessages.length);
          return sortedMessages;
        });
      }
      
    } catch (err) {
      console.error('加载历史消息失败:', err);
      
      // 显示错误消息给用户
      if (replaceAll) {
        setMessages([{
          type: 'system',
          content: `⚠️ 加载审判记录失败：${(err as Error).message}。请刷新页面重试。`,
          timestamp: new Date().toISOString()
        }]);
      } else {
        // 如果不是完全替换模式，在现有消息基础上添加错误提示
        setMessages(prev => [...prev, {
          type: 'system',
          content: `⚠️ 加载部分消息失败，显示可能不完整。`,
          timestamp: new Date().toISOString()
        }]);
      }
    }
  }, [gameId]);

  const connectWebSocketRef = useRef<() => void>();
  const handleWebSocketMessageRef = useRef<(message: ChatMessage) => void>();

  const connectWebSocket = useCallback(() => {
    if (!gameId) return;

    // 防止重复连接
    if (wsRef.current && (wsRef.current.readyState === WebSocket.CONNECTING || wsRef.current.readyState === WebSocket.OPEN)) {
      console.log('🔌 WebSocket连接已存在，跳过重复连接');
      return;
    }

    console.log('🔌 开始建立WebSocket连接...', gameId);

    // 如果已有连接，先关闭
    if (wsRef.current) {
      console.log('🔌 关闭现有连接');
      try {
        wsRef.current.close();
      } catch (e) {
        console.warn('关闭WebSocket连接时出错:', e);
      }
      wsRef.current = null;
    }

    const wsUrl = `ws://localhost:8001/api/ws/game/${gameId}`;
    console.log('🔌 连接地址:', wsUrl);
    const ws = new WebSocket(wsUrl);
    (ws as any)._connectTime = Date.now(); // 记录连接时间用于后续判断
    wsRef.current = ws;
    setWsConnectionStatus('connecting');

    ws.onopen = async () => {
      console.log('WebSocket连接已建立');
      const wasReconnecting = wsConnectionStatus === 'reconnecting';
      setWsConnectionStatus('connected');
      setHasShownDisconnectionMessage(false);
      
      // 启动心跳机制，每30秒发送一次ping
      const heartbeatInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          try {
            ws.send(JSON.stringify({
              type: 'ping',
              timestamp: Date.now()
            }));
          } catch (error) {
            console.error('发送心跳失败:', error);
            clearInterval(heartbeatInterval);
          }
        } else {
          clearInterval(heartbeatInterval);
        }
      }, 30000); // 30秒间隔
      
      // 将心跳定时器保存到WebSocket对象上，以便清理
      (ws as any)._heartbeatInterval = heartbeatInterval;
      
      // 清理所有连接中断相关的系统消息
      setMessages(prev => prev.filter(msg => 
        !(msg.type === 'system' && 
          msg.content && 
          msg.content.includes('连接中断'))
      ));
      
      // 只有在重连成功时才重新加载历史消息
      if (!isHistoryMode && wasReconnecting) {
        console.log('🔄 重连成功，重新同步历史消息...');
        try {
          await loadHistoryMessages(false, true); // 使用重连过滤模式
        } catch (err) {
          console.error('重连时同步历史消息失败:', err);
        }
      }
    };

    ws.onmessage = (event) => {
      try {
        const message: ChatMessage = JSON.parse(event.data);
        if (handleWebSocketMessageRef.current) {
          handleWebSocketMessageRef.current(message);
        }
      } catch (error) {
        console.error('解析WebSocket消息失败:', error);
      }
    };

    ws.onclose = (event) => {
      console.log('WebSocket连接已关闭', event.code, event.reason);
      
      // 清理心跳定时器
      if ((ws as any)._heartbeatInterval) {
        clearInterval((ws as any)._heartbeatInterval);
      }
      
      // 只有在连接曾经成功过才设置为disconnected，避免初始连接就显示断开警告
      if (wsConnectionStatus === 'connected') {
        setWsConnectionStatus('disconnected');
      }
      
      // 只有在非正常关闭且仍在游戏页面时才重连
      // 增加额外条件：连接曾经成功过且存在时间超过3秒，避免初始连接问题
      const wasConnected = wsConnectionStatus === 'connected';
      const connectionAge = ws.readyState === WebSocket.CLOSED ? Date.now() - (ws as any)._connectTime : 0;
      
      if (event.code !== 1000 && gameId && wsRef.current === ws && !isHistoryMode && 
          wasConnected && connectionAge > 3000) {
        console.log('5秒后尝试重连...');
        setWsConnectionStatus('reconnecting');
        
        // 只有在首次断开连接时才显示连接中断信息
        if (!hasShownDisconnectionMessage) {
          setMessages(prev => [...prev, {
            type: 'system',
            content: '⚠️ 连接中断，正在尝试重新连接...',
            timestamp: new Date().toISOString()
          }]);
          setHasShownDisconnectionMessage(true);
        }
        
        setTimeout(() => {
          // 再次检查是否仍需要重连
          if (gameId && wsRef.current === ws && !isHistoryMode && connectWebSocketRef.current) {
            connectWebSocketRef.current();
          }
        }, 5000);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket错误:', error);
      // 不要立即设置为disconnected，让onclose处理状态变更
      // 避免短暂的连接错误触发警告
    };
  }, [gameId, isHistoryMode, hasShownDisconnectionMessage, loadHistoryMessages, wsConnectionStatus]);

  connectWebSocketRef.current = connectWebSocket;

  const loadInitialData = useCallback(async () => {
    if (!gameId || isInitializingRef.current) return;
    
    try {
      isInitializingRef.current = true;
      console.log('🔄 开始加载游戏初始数据...');
      
      // 一次性获取所有需要的数据
      const [gameData, statusData] = await Promise.all([
        gameService.getGame(parseInt(gameId)),
        gameService.getGameStatus(parseInt(gameId))
      ]);
      
      console.log('📊 游戏状态:', gameData.status);
      
      // 更新游戏数据和状态
      setGame(gameData);
      setGameStatus(statusData);
      
      // 根据游戏状态设置gamePhase - 使用函数式更新避免依赖
      setGamePhase(prevPhase => {
        if (!prevPhase) {
          switch (gameData.status) {
            case 'preparing':
              return '准备中';
            case 'running':
              return '辩论中';
            case 'finished':
              return '审判结束';
            default:
              return '';
          }
        }
        return prevPhase;
      });
      
      if (gameData.status === 'finished') {
        // 游戏已结束，加载历史记录（完全替换）
        console.log('🏁 游戏已结束，加载历史记录');
        setIsHistoryMode(true);
        setHasShownDisconnectionMessage(false); // 重置连接中断消息状态
        await loadHistoryMessages(true);
      } else {
        // 游戏进行中，智能合并历史记录和实时消息
        console.log('🎮 游戏进行中，准备建立实时连接');
        setIsHistoryMode(false);
        setHasShownDisconnectionMessage(false); // 重置连接中断消息状态
        await loadHistoryMessages(false); // 智能合并历史记录，保留实时消息
        
        // 确保WebSocket连接建立
        console.log('🔌 建立WebSocket连接...');
        if (connectWebSocketRef.current) {
          connectWebSocketRef.current(); // 使用ref来避免依赖问题
        }
      }
      
      setError(null);
    } catch (err) {
      console.error('初始化数据失败:', err);
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
      isInitializingRef.current = false;
    }
  }, [gameId, loadHistoryMessages]);

  useEffect(() => {
    if (gameId) {
      // 重置初始化标志并调用初始化
      isInitializingRef.current = false;
      loadInitialData();
      
      // 设置定时刷新游戏数据（但不重复加载历史消息）
      const interval = setInterval(async () => {
        try {
          const [gameData, statusData] = await Promise.all([
            gameService.getGame(parseInt(gameId)),
            gameService.getGameStatus(parseInt(gameId))
          ]);
          setGame(gameData);
          setGameStatus(statusData);
        } catch (err) {
          console.error('定时刷新游戏数据失败:', err);
        }
      }, 10000);
      
      return () => {
        clearInterval(interval);
        if (wsRef.current) {
          wsRef.current.close();
        }
      };
    }
  }, [gameId, loadInitialData]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 调试：监控话题变化
  useEffect(() => {
    console.log('📋 当前话题状态变化:', currentTopic);
  }, [currentTopic]);

  // 监听游戏状态变化，确保游戏开始时立即建立连接
  useEffect(() => {
    if (game && game.status === 'running' && !isHistoryMode && 
        wsConnectionStatus !== 'connected' && wsConnectionStatus !== 'connecting' && 
        (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED)) {
      console.log('🔄 游戏已开始，立即建立WebSocket连接...');
      connectWebSocket();
    }
  }, [game, isHistoryMode, wsConnectionStatus, connectWebSocket]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // 辅助函数：渲染已完成的内容（包含完整的think标签）
  const renderCompletedContent = (content: string) => {
    if (!content) return '';
    
    const parts: React.ReactElement[] = [];
    let lastIndex = 0;
    const thinkRegex = /<think>([\s\S]*?)<\/think>/gi;
    let match;
    let hasThinkContent = false;
    
    while ((match = thinkRegex.exec(content)) !== null) {
      // 添加思考过程之前的正常内容
      if (match.index > lastIndex) {
        const normalText = content.slice(lastIndex, match.index);
        if (normalText.trim()) {
          parts.push(
            <span key={`normal-${lastIndex}`}>{normalText}</span>
          );
        }
      }
      
      // 添加思考过程（已完成的思考显示为灰色）
      const thinkContent = match[1];
      if (thinkContent.trim()) {
        hasThinkContent = true;
        parts.push(
          <span 
            key={`think-${match.index}`} 
            style={{ 
              color: '#888', 
              fontStyle: 'italic',
              backgroundColor: '#f5f5f5',
              padding: '2px 4px',
              borderRadius: '3px',
              fontSize: '0.9em'
            }}
          >
            💭 {thinkContent.trim()}
          </span>
        );
      }
      
      lastIndex = match.index + match[0].length;
    }
    
    // 添加剩余的正常内容
    if (lastIndex < content.length) {
      const remainingText = content.slice(lastIndex);
      if (remainingText.trim()) {
        // 如果有思考过程且有剩余内容，在思考过程后添加换行
        if (hasThinkContent && parts.length > 0) {
          parts.push(<br key={`break-${lastIndex}`} />);
        }
        parts.push(
          <span key={`normal-${lastIndex}`}>{remainingText}</span>
        );
      }
    }
    
    // 如果没有找到think标签，直接返回原内容
    if (parts.length === 0) {
      return content;
    }
    
    return (
      <React.Fragment>
        {parts.map((part, index) => part)}
      </React.Fragment>
    );
  };

  const renderMessageContent = (content?: string, isStreaming?: boolean) => {
    if (!content) return '';
    
    // 如果是流式输出，先检查是否有未完成的思考过程
    if (isStreaming) {
      // 检查是否有未闭合的<think>标签
      const openThinkIndex = content.lastIndexOf('<think>');
      const closeThinkIndex = content.lastIndexOf('</think>');
      
      if (openThinkIndex > -1 && (closeThinkIndex === -1 || openThinkIndex > closeThinkIndex)) {
        // 有未完成的思考过程，保持正常颜色显示
        const beforeThink = content.slice(0, openThinkIndex);
        const thinkContent = content.slice(openThinkIndex + 7); // 跳过 '<think>'
        
        // 检查思考过程之前是否有已完成的思考过程
        const hasCompletedThink = beforeThink.includes('</think>');
        
        return (
          <React.Fragment>
            {renderCompletedContent(beforeThink)}
            {hasCompletedThink && beforeThink.trim() && <br />}
            <span 
              style={{ 
                fontStyle: 'italic',
                backgroundColor: '#f9f9f9',
                padding: '2px 4px',
                borderRadius: '3px',
                fontSize: '0.9em'
              }}
            >
              💭 {thinkContent}
            </span>
          </React.Fragment>
        );
      }
    }
    
    // 处理已完成的内容（包含完整的think标签或非流式输出）
    return renderCompletedContent(content);
  };

  const handleWebSocketMessage = useCallback((message: ChatMessage) => {
    // 流式消息类型不需要去重，因为它们共享同一个message_id但需要分别处理
    const streamingMessageTypes = [
      'message_start', 'message_chunk', 'message_complete', 'message_error',
      'defense_start', 'defense_chunk', 'defense_complete', 'defense_error'
    ];
    
    // 检查消息是否有ID且已经处理过（排除流式消息）
    const messageId = (message as any).message_id;
    if (messageId && !streamingMessageTypes.includes(message.type)) {
      if (processedMessageIds.has(messageId)) {
        // 只在开发模式下记录重复消息
        if (process.env.NODE_ENV === 'development' && 
            message.type !== 'pong' && 
            message.type !== 'system_message') {
          console.log('🔄 忽略重复消息:', messageId, message.type);
        }
        return;
      }
      // 记录已处理的消息ID
      setProcessedMessageIds(prev => {
        const newSet = new Set(prev);
        newSet.add(messageId);
        return newSet;
      });
    }

    // 只在开发模式下记录非流式消息，排除常见的重复消息
    if (process.env.NODE_ENV === 'development' && 
        !streamingMessageTypes.includes(message.type) &&
        message.type !== 'pong' && 
        message.type !== 'system_message') {
      console.log('📨 处理消息:', messageId, message.type);
    }

    switch (message.type) {
      case 'connected':
        console.log('已连接到游戏');
        setWsConnectionStatus('connected');
        // 重连恢复消息现在统一在 ws.onopen 中处理
        break;
      
      case 'pong':
        // 收到心跳回应，连接正常（减少日志输出）
        break;
      
      case 'system_message':
        // 减少系统消息日志输出
        if (process.env.NODE_ENV === 'development') {
          console.log('🔔 收到系统消息:', message.content?.substring(0, 30) + '...');
        }
        
        // 检查是否已存在相同内容的系统消息（避免重复显示）
        // 但是要允许某些重要的阶段转换消息重复显示
        const content = message.content || '';
        const isImportantPhaseMessage = content.includes('最终申辞阶段开始') || 
                                      content.includes('追加辩论阶段开始') || 
                                      content.includes('最终投票开始') ||
                                      content.includes('追加投票开始');
        
        if (!isImportantPhaseMessage && processedSystemMessages.has(content)) {
          // 减少重复系统消息日志
          break;
        }
        
        // 添加到已处理的系统消息集合
        setProcessedSystemMessages(prev => {
          const newSet = new Set(prev);
          newSet.add(message.content || '');
          return newSet;
        });
        
        // 添加新的系统消息到界面
        setMessages(prev => [...prev, {
          type: 'system',
          content: message.content,
          timestamp: message.timestamp || new Date().toISOString()
        }]);
        break;
      
      case 'round_start':
        console.log('🎯 收到round_start消息:', {
          topic: message.topic,
          topicLength: message.topic ? message.topic.length : 0,
          isResume: (message as any).is_resume
        });
        
        setCurrentTopic(message.topic || '');
        setGamePhase('辩论中');
        
        // 确保话题不为空
        const topicText = message.topic || '未指定话题';
        console.log('📝 设置话题为:', topicText);
        
        // 系统消息现在通过后端的system_message广播，无需前端重新加载历史
        console.log('✅ 轮次开始状态已更新，系统消息将通过WebSocket接收');
        break;
      
      case 'new_message':
        setMessages(prev => [...prev, {
          type: 'chat',
          participant_id: message.participant_id,
          participant_name: message.participant_name,
          content: message.content,
          timestamp: message.timestamp,
          sequence: message.sequence
        }]);
        break;
      
      // 流式消息处理
      case 'message_start':
        // AI开始发言
        console.log(`🗣️ ${message.participant_name} 开始发言`);
        setMessages(prev => [...prev, {
          type: 'chat',
          participant_id: message.participant_id,
          participant_name: message.participant_name,
          content: '',
          timestamp: message.timestamp,
          message_id: message.message_id,
          isStreaming: true,
          streamingContent: ''
        }]);
        break;
      
      case 'message_chunk':
        // 接收到AI发言片段
        setMessages(prev => {
          const newMessages = [...prev];
          // 找到对应的流式消息
          const streamingMessageIndex = newMessages.findIndex(msg => 
            msg.message_id === message.message_id && msg.isStreaming
          );
          
          if (streamingMessageIndex !== -1) {
            newMessages[streamingMessageIndex] = {
              ...newMessages[streamingMessageIndex],
              streamingContent: (newMessages[streamingMessageIndex].streamingContent || '') + message.chunk
            };
          }
          return newMessages;
        });
        break;
      
      case 'message_complete':
        // AI发言完成
        console.log(`✅ ${message.participant_name} 发言结束`);
        setMessages(prev => {
          const newMessages = [...prev];
          const streamingMessageIndex = newMessages.findIndex(msg => 
            msg.message_id === message.message_id && msg.isStreaming
          );
          
          if (streamingMessageIndex !== -1) {
            newMessages[streamingMessageIndex] = {
              ...newMessages[streamingMessageIndex],
              content: message.content,
              isStreaming: false,
              streamingContent: undefined
            };
          }
          return newMessages;
        });
        
        // 标记这个消息已完成，避免重复处理
        if (message.message_id) {
          setProcessedMessageIds(prev => {
            const newSet = new Set(prev);
            newSet.add(message.message_id!);
            return newSet;
          });
        }
        break;
      
      case 'message_error':
        // AI发言出错
        console.log(`❌ ${message.participant_name || '未知参与者'} 发言出错: ${message.error}`);
        setMessages(prev => {
          const newMessages = [...prev];
          const streamingMessageIndex = newMessages.findIndex(msg => 
            msg.message_id === message.message_id && msg.isStreaming
          );
          
          if (streamingMessageIndex !== -1) {
            newMessages[streamingMessageIndex] = {
              ...newMessages[streamingMessageIndex],
              content: `[发言错误: ${message.error}]`,
              isStreaming: false,
              streamingContent: undefined
            };
          }
          return newMessages;
        });
        break;
      
      // 最终申辞流式处理
      case 'defense_start':
        // 开始最终申辞
        console.log(`🛡️ ${message.participant_name} 开始最终申辞`);
        setMessages(prev => [...prev, {
          type: 'chat',
          participant_id: message.participant_id,
          participant_name: message.participant_name + ' (最终申辞)',
          content: '',
          timestamp: message.timestamp,
          message_id: message.message_id,
          isStreaming: true,
          streamingContent: ''
        }]);
        break;
      
      case 'defense_chunk':
        // 接收到申辞片段
        setMessages(prev => {
          const newMessages = [...prev];
          const streamingMessageIndex = newMessages.findIndex(msg => 
            msg.message_id === message.message_id && msg.isStreaming
          );
          
          if (streamingMessageIndex !== -1) {
            newMessages[streamingMessageIndex] = {
              ...newMessages[streamingMessageIndex],
              streamingContent: (newMessages[streamingMessageIndex].streamingContent || '') + message.chunk
            };
          }
          return newMessages;
        });
        break;
      
      case 'defense_complete':
        // 申辞完成
        console.log(`✅ ${message.participant_name} 最终申辞结束`);
        setMessages(prev => {
          const newMessages = [...prev];
          const streamingMessageIndex = newMessages.findIndex(msg => 
            msg.message_id === message.message_id && msg.isStreaming
          );
          
          if (streamingMessageIndex !== -1) {
            newMessages[streamingMessageIndex] = {
              ...newMessages[streamingMessageIndex],
              content: message.content,
              isStreaming: false,
              streamingContent: undefined
            };
          }
          return newMessages;
        });
        
        // 标记这个申辞已完成，避免重复处理
        if (message.message_id) {
          setProcessedMessageIds(prev => {
            const newSet = new Set(prev);
            newSet.add(message.message_id!);
            return newSet;
          });
        }
        break;
      
      case 'defense_error':
        // 申辞出错
        console.log(`❌ ${message.participant_name || '未知参与者'} 申辞出错: ${message.error}`);
        setMessages(prev => {
          const newMessages = [...prev];
          const streamingMessageIndex = newMessages.findIndex(msg => 
            msg.message_id === message.message_id && msg.isStreaming
          );
          
          if (streamingMessageIndex !== -1) {
            newMessages[streamingMessageIndex] = {
              ...newMessages[streamingMessageIndex],
              content: `[申辞错误: ${message.error}]`,
              isStreaming: false,
              streamingContent: undefined
            };
          }
          return newMessages;
        });
        break;
      
      case 'voting_start':
        setGamePhase('最终投票');
        setMessages(prev => [...prev, {
          type: 'system',
          content: '🗳️ 法庭辩论结束！现在进行最终投票，选出AI间谍！',
          timestamp: new Date().toISOString()
        }]);
        break;
      
      case 'initial_voting_result':
        // 检查连接状态，确保数据完整性
        if (wsConnectionStatus !== 'connected') {
          console.warn('连接不稳定时忽略初投票结果');
          break;
        }
        
        // 投票表格现在由后端直接广播voting_table类型消息，此处不再重复创建
        break;
      
      case 'final_defense_start':
        setGamePhase('最终申辞');
        // 系统消息由后端统一广播，不在前端重复创建
        break;
      
      case 'final_defense_speech':
        setMessages(prev => [...prev, {
          type: 'chat',
          participant_id: message.participant_id,
          participant_name: message.participant_name,
          content: message.content,
          timestamp: message.timestamp,
          sequence: message.sequence
        }]);
        break;
      
      case 'final_voting_start':
        setGamePhase('最终投票');
        // 系统消息由后端统一广播，不在前端重复创建
        break;
      
      case 'final_voting_result':
        // 检查连接状态，确保数据完整性
        if (wsConnectionStatus !== 'connected') {
          console.warn('连接不稳定时忽略最终投票结果');
          break;
        }
        
        // 投票表格现在由后端直接广播voting_table类型消息，此处不再重复创建
        break;
      
      case 'additional_debate_start':
        setGamePhase('追加辩论');
        // 系统消息由后端统一广播，不在前端重复创建
        break;
      
      case 'additional_debate_speech':
        setMessages(prev => [...prev, {
          type: 'chat',
          participant_id: message.participant_id,
          participant_name: message.participant_name,
          content: message.content,
          timestamp: message.timestamp,
          sequence: message.sequence
        }]);
        break;
      
      case 'additional_voting_start':
        setGamePhase('追加投票');
        // 系统消息现在由后端通过system_message事件发送，不需要前端重复添加
        break;
      
      case 'voting_result':
        // 检查连接状态，如果连接不稳定则忽略可能不完整的投票结果
        if (wsConnectionStatus !== 'connected') {
          console.warn('连接不稳定时忽略投票结果消息');
          break;
        }
        
        const eliminatedPlayer = message.eliminated_player;
        const winners = message.winners || [];
        
        // 确保消息包含完整的投票数据
        if (!eliminatedPlayer || !eliminatedPlayer.name) {
          console.warn('投票结果数据不完整，忽略此消息');
          break;
        }
        
        setMessages(prev => [...prev, {
          type: 'system',
          content: `🎯 投票结果：${eliminatedPlayer.name} 被选为最可疑者！得票数：${eliminatedPlayer.vote_count || 0}`,
          timestamp: new Date().toISOString()
        }]);
        
        // 显示获胜者
        if (winners.length > 0) {
          const winnerNames = winners.map((w: any) => w.name).join('、');
          setMessages(prev => [...prev, {
            type: 'system',
            content: `🎉 获胜者：${winnerNames}`,
            timestamp: new Date().toISOString()
          }]);
        }
        
        // 显示投票详情
        if (message.vote_details?.length) {
          setMessages(prev => [...prev, {
            type: 'system',
            content: '📊 投票详情：\n' + (message.vote_details || []).map((vote: any) => 
              `${vote.voter_name} → ${vote.target_name}：${vote.reason}`
            ).join('\n'),
            timestamp: new Date().toISOString()
          }]);
        }
        
        refreshGameData();
        break;
      
      case 'game_ended':
        // 检查连接状态，确保游戏结束消息的完整性
        if (wsConnectionStatus !== 'connected') {
          console.warn('连接不稳定时忽略游戏结束消息');
          break;
        }
        
        setGamePhase('审判结束');
        const endResultMessage = message.result_message || 
          `🎯 审判结束！${message.eliminated_player?.name} 被选为最可疑者！`;
        
        setMessages(prev => [...prev, {
          type: 'system',
          content: endResultMessage,
          timestamp: new Date().toISOString()
        }]);
        
        refreshGameData();
        break;
      
      case 'voting_table':
        // 检查是否已存在相同的投票表格（使用更精确的去重逻辑）
        const newTimestamp = message.timestamp || new Date().toISOString();
        const newVotingDataHash = message.voting_data ? 
          `${message.voting_data.total_votes}_${message.voting_data.candidates?.length || 0}_${JSON.stringify(message.voting_data).slice(0, 50)}` : 
          'empty';
        
        const existingVotingTable = messages.find(msg => {
          if (msg.type !== 'voting_table') return false;
          
          // 如果时间戳相近（10秒内）且投票数据相似，认为是重复
          if (msg.timestamp && newTimestamp) {
            const timeDiff = Math.abs(new Date(msg.timestamp).getTime() - new Date(newTimestamp).getTime());
            if (timeDiff < 10000) { // 10秒内
              const existingHash = msg.voting_data ? 
                `${msg.voting_data.total_votes}_${msg.voting_data.candidates?.length || 0}_${JSON.stringify(msg.voting_data).slice(0, 50)}` : 
                'empty';
              return existingHash === newVotingDataHash;
            }
          }
          
          return false;
        });
        
        if (existingVotingTable) {
          break;
        }
        
        // 直接显示后端广播的投票表格
        setMessages(prev => [...prev, {
          type: 'voting_table',
          voting_data: message.voting_data,
          title: message.title,
          timestamp: newTimestamp
        }]);
        break;
      
      default:
        console.log('未知消息类型:', message.type);
    }
  }, [processedMessageIds, refreshGameData, wsConnectionStatus, messages.length, processedSystemMessages]);

  handleWebSocketMessageRef.current = handleWebSocketMessage;

  const handleStartGame = async () => {
    if (!gameId) return;
    
    try {
      await gameService.startGame(parseInt(gameId));
      
      // 立即设置为非历史模式
      setIsHistoryMode(false);
      
      // 更新游戏数据
      await refreshGameData();
      
      // 确保建立WebSocket连接
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        setWsConnectionStatus('connecting');
        connectWebSocket();
      }
    } catch (err) {
      alert('开始游戏失败: ' + (err as Error).message);
    }
  };

  const handleStopGame = async () => {
    if (!gameId) return;
    
    try {
      await gameService.stopGame(parseInt(gameId));
      refreshGameData();
    } catch (err) {
      alert('停止游戏失败: ' + (err as Error).message);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'success';
      case 'finished': return 'default';
      case 'preparing': return 'warning';
      default: return 'default';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'running': return '审判进行中';
      case 'finished': return '审判结束';
      case 'preparing': return '准备审判';
      default: return status;
    }
  };

  const formatDateTime = (timestamp: string | Date) => {
    let date: Date;
    
    if (typeof timestamp === 'string') {
      // 解析时间戳字符串
      date = new Date(timestamp);
      
      // 检查是否解析成功
      if (isNaN(date.getTime())) {
        return '无效时间';
      }
    } else {
      date = timestamp;
    }
    
    // 使用Intl.DateTimeFormat确保使用本地时区
    try {
      const formatter = new Intl.DateTimeFormat(navigator.language, {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
      });
      
      return formatter.format(date);
    } catch (error) {
      console.error('时间格式化错误:', error);
      // 降级到基本的toLocaleString
      return date.toLocaleString();
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return formatDateTime(timestamp);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress size={60} />
      </Box>
    );
  }

  if (error || !game || !gameStatus) {
    return (
      <Box>
        <Button
          startIcon={<BackIcon />}
          onClick={() => navigate('/')}
          sx={{ mb: 2 }}
        >
          返回首页
        </Button>
        <Alert severity="error">
          {error || '游戏不存在'}
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      {/* 头部控制栏 */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box display="flex" alignItems="center">
          <Button
            startIcon={<BackIcon />}
            onClick={() => navigate('/')}
            sx={{ mr: 2 }}
          >
            返回首页
          </Button>
          <Typography variant="h4" component="h1">
            游戏 #{game.id}
          </Typography>
          <Chip
            label={getStatusText(game.status)}
            color={getStatusColor(game.status) as any}
            sx={{ ml: 2 }}
          />
          {gamePhase && gamePhase !== getStatusText(game.status) && (
            <Chip
              label={gamePhase}
              color="primary"
              variant="outlined"
              sx={{ ml: 1 }}
            />
          )}
          {/* 连接状态显示 */}
          {!isHistoryMode && (
            <Chip
              label={
                wsConnectionStatus === 'connected' ? '🟢 已连接' :
                wsConnectionStatus === 'connecting' ? '🟡 连接中' :
                wsConnectionStatus === 'reconnecting' ? '🟡 重连中' :
                '🔴 连接断开'
              }
              color={
                wsConnectionStatus === 'connected' ? 'success' :
                wsConnectionStatus === 'disconnected' ? 'error' :
                'warning'
              }
              variant="outlined"
              size="small"
              sx={{ ml: 1 }}
            />
          )}
        </Box>
        
        <Box>
          <Button
            startIcon={<RefreshIcon />}
            onClick={refreshGameData}
            sx={{ mr: 1 }}
          >
            刷新
          </Button>
          {game.status === 'preparing' && (
            <Button
              variant="contained"
              startIcon={<PlayIcon />}
              onClick={handleStartGame}
              sx={{ mr: 1 }}
            >
              开始审判
            </Button>
          )}
          {game.status === 'running' && (
            <Button
              variant="outlined"
              color="error"
              startIcon={<StopIcon />}
              onClick={handleStopGame}
            >
              停止审判
            </Button>
          )}
        </Box>
      </Box>

      {/* 游戏信息和参与者 */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* 游戏信息 */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              审判信息
            </Typography>
            
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">
                审判开始: {formatDateTime(game.start_time)}
              </Typography>
              {game.end_time && (
                <Typography variant="body2" color="text.secondary">
                  审判结束: {formatDateTime(game.end_time)}
                </Typography>
              )}
              <Typography variant="body2" color="text.secondary">
                当前阶段: {gamePhase || getStatusText(game.status)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                参与者总数: {gameStatus.participants.length}
              </Typography>
            </Box>

            {isHistoryMode && (
              <Alert severity="info" sx={{ mb: 2 }}>
                正在观看审判回放
              </Alert>
            )}

            {currentTopic && (
              <Card variant="outlined" sx={{ mt: 2 }}>
                <CardContent>
                  <Typography variant="subtitle2" color="primary" gutterBottom>
                    当前辩论焦点
                  </Typography>
                  <Typography variant="body2">
                    {currentTopic}
                  </Typography>
                </CardContent>
              </Card>
            )}
          </Paper>
        </Grid>

        {/* 参与者列表 */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              法庭参与者 ({gameStatus.participants.length})
            </Typography>
            
            {gameStatus.participants.length === 0 ? (
              <Alert severity="info">
                正在初始化参与者...
              </Alert>
            ) : (
              <List>
                {gameStatus.participants.map((participant, index) => (
                  <ListItem key={participant.id || index} divider>
                    <ListItemAvatar>
                      <Avatar sx={{ 
                        bgcolor: participant.status === 'active' ? 'success.main' : 'error.main' 
                      }}>
                        <PersonIcon />
                      </Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={participant.human_name || `参与者 ${index + 1}`}
                      secondary={
                        <React.Fragment>
                          <span style={{ display: 'block', fontSize: '0.875rem', color: 'rgba(0, 0, 0, 0.6)' }}>
                            模型: {participant.model_name || '未知'}
                          </span>
                          {participant.background && (
                            <span style={{ display: 'block', fontSize: '0.875rem', color: 'rgba(0, 0, 0, 0.6)' }}>
                              背景: {participant.background}
                            </span>
                          )}
                          {participant.personality && (
                            <span style={{ display: 'block', fontSize: '0.875rem', color: 'rgba(0, 0, 0, 0.6)' }}>
                              性格: {participant.personality}
                            </span>
                          )}
                        </React.Fragment>
                      }
                    />
                    <Chip
                      label={participant.status === 'active' ? '存活' : '淘汰'}
                      color={participant.status === 'active' ? 'success' : 'default'}
                      size="small"
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* 实时聊天面板 */}
      <Paper sx={{ p: 3, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          {game.status === 'finished' ? '审判回放' : '法庭实况'}
        </Typography>
        
        {/* 连接状态警告 - 只在非历史模式且真正需要显示警告时显示 */}
        {!isHistoryMode && game && game.status === 'running' && (
          (wsConnectionStatus === 'reconnecting' || 
           (wsConnectionStatus === 'disconnected' && hasShownDisconnectionMessage)) && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            {wsConnectionStatus === 'reconnecting' && '🟡 连接中断，正在重新连接...'}
            {wsConnectionStatus === 'disconnected' && '🔴 与服务器连接断开，显示的信息可能不完整'}
          </Alert>
        ))}
        
        <Box sx={{ 
          height: '800px', 
          border: 1, 
          borderColor: 'divider', 
          borderRadius: 1, 
          p: 2,
          overflow: 'auto',
          bgcolor: 'background.default'
        }}>
          {messages.length === 0 ? (
            <Box textAlign="center" sx={{ mt: 4 }}>
              <Typography variant="body2" color="text.secondary">
                {game.status === 'finished' 
                  ? '暂无审判记录'
                  : game.status === 'preparing' 
                    ? '法庭准备中，等待审判开始...' 
                    : game.status === 'running'
                      ? '⚖️ 审判进行中，等待法庭消息...'
                      : '正在加载审判记录...'
                }
              </Typography>
            </Box>
          ) : (
            <Box>
              {messages.map((message, index) => (
                <Box key={`msg-${index}-${message.type}`} sx={{ mb: 2 }}>
                  {message.type === 'system' ? (
                    <Box sx={{ 
                      textAlign: 'center', 
                      p: 1, 
                      bgcolor: 'info.light', 
                      borderRadius: 1,
                      color: 'white'
                    }}>
                      <Typography variant="body2" component="div" sx={{ whiteSpace: 'pre-wrap' }}>
                        {message.content}
                      </Typography>
                    </Box>
                  ) : message.type === 'voting_table' ? (
                    <VotingResultTable 
                      votingData={message.voting_data!}
                      title={message.title || '投票结果'}
                    />
                  ) : (
                    <Card variant="outlined" sx={{ mb: 1 }}>
                      <CardContent sx={{ p: 2 }}>
                        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                          <Typography variant="subtitle2" color="primary">
                            {message.participant_name}
                            {message.type === 'final_defense' && ' (最终申辞)'}
                            {message.type === 'additional_debate' && ' (追加辩论)'}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {message.timestamp ? formatTimestamp(message.timestamp) : ''}
                          </Typography>
                        </Box>
                        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                          {message.isStreaming 
                            ? (
                              <span>
                                {renderMessageContent(message.streamingContent || '', true)}
                                <span 
                                  style={{ 
                                    opacity: 0.7, 
                                    animation: 'blink 1s infinite',
                                    marginLeft: '2px' 
                                  }}
                                >
                                  |
                                </span>
                              </span>
                            )
                            : renderMessageContent(message.content, false)
                          }
                        </Typography>
                      </CardContent>
                    </Card>
                  )}
                </Box>
              ))}
              <div ref={messagesEndRef} />
            </Box>
          )}
        </Box>
      </Paper>
    </Box>
  );
};

export default GameRoom; 