"""
Ollama集成服务
"""

import httpx
import asyncio
from typing import List, Optional
from app.core.config import settings
from app.schemas.ollama_schemas import ModelInfo, ChatResponse

class OllamaService:
    """Ollama API集成服务"""
    
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.timeout = settings.OLLAMA_TIMEOUT
    
    async def get_available_models(self) -> List[ModelInfo]:
        """获取可用模型列表"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            
            models = []
            for model in data.get("models", []):
                details = model.get("details", {})
                models.append(ModelInfo(
                    name=model["name"],
                    size=str(model.get("size", 0)) if model.get("size") else None,
                    format=details.get("format"),
                    family=details.get("family"),
                    families=details.get("families", []),
                    parameter_size=details.get("parameter_size"),
                    quantization_level=details.get("quantization_level")
                ))
            return models
    
    async def chat(self, model: str, message: str, context: Optional[str] = None) -> ChatResponse:
        """与模型对话"""
        payload = {
            "model": model,
            "prompt": message,
            "stream": False
        }
        
        if context:
            payload["context"] = context
            
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            
            return ChatResponse(
                model=data["model"],
                message=data["response"],
                done=data["done"],
                total_duration=data.get("total_duration"),
                load_duration=data.get("load_duration"),
                prompt_eval_count=data.get("prompt_eval_count"),
                prompt_eval_duration=data.get("prompt_eval_duration"),
                eval_count=data.get("eval_count"),
                eval_duration=data.get("eval_duration")
            )
    
    async def check_health(self) -> bool:
        """检查Ollama服务健康状态"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False 