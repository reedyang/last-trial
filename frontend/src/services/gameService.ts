/**
 * 游戏管理API服务
 */

const API_BASE_URL = 'http://localhost:8001/api';

export interface GameCreateRequest {
  max_round_time?: number;
  selected_models?: string[];
}

export interface Game {
  id: number;
  status: string;
  start_time: string;
  end_time?: string;
  total_rounds: number;
  winner_count: number;
  created_at: string;
}

export interface GameStatus {
  game_id: number;
  status: string;
  current_round: number;
  participants: any[];
  active_participants: number;
  eliminated_participants: number;
}

export const gameService = {
  // 创建游戏
  async createGame(gameData: GameCreateRequest) {
    const response = await fetch(`${API_BASE_URL}/game/create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(gameData),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create game');
    }

    return response.json();
  },

  // 获取游戏列表
  async getGames() {
    const response = await fetch(`${API_BASE_URL}/game/`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch games');
    }

    return response.json();
  },

  // 获取游戏信息
  async getGame(gameId: number) {
    const response = await fetch(`${API_BASE_URL}/game/${gameId}`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch game');
    }

    return response.json();
  },

  // 获取游戏状态
  async getGameStatus(gameId: number) {
    const response = await fetch(`${API_BASE_URL}/game/${gameId}/status`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch game status');
    }

    return response.json();
  },

  // 获取游戏历史聊天记录
  async getGameMessages(gameId: number) {
    const response = await fetch(`${API_BASE_URL}/game/${gameId}/messages`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch game messages');
    }

    return response.json();
  },

  // 开始游戏
  async startGame(gameId: number) {
    const response = await fetch(`${API_BASE_URL}/game/${gameId}/start`, {
      method: 'POST',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to start game');
    }

    return response.json();
  },

  // 停止游戏
  async stopGame(gameId: number) {
    const response = await fetch(`${API_BASE_URL}/game/${gameId}/stop`, {
      method: 'POST',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to stop game');
    }

    return response.json();
  },

  // 删除游戏
  async deleteGame(gameId: number) {
    const response = await fetch(`${API_BASE_URL}/game/${gameId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete game');
    }

    return response.json();
  },
}; 