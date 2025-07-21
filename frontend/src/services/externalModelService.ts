/**
 * 外部AI模型管理服务
 */

export enum APIType {
  OPENAI = 'OPENAI',
  OPENWEBUI = 'OPENWEBUI'
}

export interface ExternalModel {
  id: number;
  name: string;
  api_type: APIType;
  api_url: string;
  model_id: string;
  api_key?: string;
  description?: string;
  is_active: boolean;
  last_tested?: string;
  test_status?: string;
  test_error?: string;
  created_at: string;
  updated_at?: string;
}

export interface ExternalModelCreate {
  name: string;
  api_type: APIType;
  api_url: string;
  model_id: string;
  api_key?: string;
  description?: string;
  is_active: boolean;
}

export interface ExternalModelUpdate {
  name?: string;
  api_type?: APIType;
  api_url?: string;
  model_id?: string;
  api_key?: string;
  description?: string;
  is_active?: boolean;
}

export interface ExternalModelTest {
  api_type: APIType;
  api_url: string;
  model_id: string;
  api_key?: string;
}

export interface ExternalModelTestResponse {
  success: boolean;
  message: string;
  response_time?: number;
  error?: string;
}

class ExternalModelService {
  private baseURL = 'http://localhost:8001/api/external-models';

  async getModels(activeOnly: boolean = false): Promise<ExternalModel[]> {
    const params = activeOnly ? '?active_only=true' : '';
    const response = await fetch(`${this.baseURL}/${params}`);
    if (!response.ok) {
      throw new Error(`获取外部模型列表失败: ${response.statusText}`);
    }
    return response.json();
  }

  async getModel(id: number): Promise<ExternalModel> {
    const response = await fetch(`${this.baseURL}/${id}`);
    if (!response.ok) {
      throw new Error(`获取外部模型失败: ${response.statusText}`);
    }
    return response.json();
  }

  async createModel(data: ExternalModelCreate): Promise<ExternalModel> {
    const response = await fetch(this.baseURL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || '创建外部模型失败');
    }
    return response.json();
  }

  async updateModel(id: number, data: ExternalModelUpdate): Promise<ExternalModel> {
    const response = await fetch(`${this.baseURL}/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || '更新外部模型失败');
    }
    return response.json();
  }

  async deleteModel(id: number): Promise<void> {
    const response = await fetch(`${this.baseURL}/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || '删除外部模型失败');
    }
  }

  async testModel(data: ExternalModelTest): Promise<ExternalModelTestResponse> {
    const response = await fetch(`${this.baseURL}/test`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || '测试外部模型失败');
    }
    return response.json();
  }

  async testExistingModel(id: number): Promise<ExternalModelTestResponse> {
    const response = await fetch(`${this.baseURL}/${id}/test`, {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || '测试外部模型失败');
    }
    return response.json();
  }
}

export const externalModelService = new ExternalModelService(); 