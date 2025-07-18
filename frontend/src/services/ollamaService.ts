/**
 * Ollama集成API服务
 */

const API_BASE = '/api/ollama';

export interface ModelInfo {
  name: string;
  size?: string;
  format?: string;
  family?: string;
  families?: string[];
  parameter_size?: string;
  quantization_level?: string;
}

export interface HealthStatus {
  status: string;
  ollama_available: boolean;
  error?: string;
}

class OllamaService {
  /**
   * 获取可用模型列表
   */
  async getModels(): Promise<ModelInfo[]> {
    const response = await fetch(`${API_BASE}/models`);
    if (!response.ok) {
      throw new Error('获取模型列表失败');
    }
    return response.json();
  }

  /**
   * 检查Ollama服务健康状态
   */
  async checkHealth(): Promise<HealthStatus> {
    try {
      const response = await fetch(`${API_BASE}/health`);
      return response.json();
    } catch (error) {
      return {
        status: 'error',
        ollama_available: false,
        error: '无法连接到Ollama服务'
      };
    }
  }

  /**
   * 与模型聊天
   */
  async chat(model: string, message: string, context?: string): Promise<any> {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model,
        message,
        context,
      }),
    });
    
    if (!response.ok) {
      throw new Error('聊天请求失败');
    }
    return response.json();
  }
}

export const ollamaService = new OllamaService(); 