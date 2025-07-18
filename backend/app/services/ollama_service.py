"""
Ollama集成服务
"""

import httpx
import asyncio
import json
from typing import List, Optional, AsyncGenerator
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
        """与模型对话（非流式）"""
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
    
    async def chat_stream(self, model: str, message: str, context: Optional[str] = None) -> AsyncGenerator[str, None]:
        """与模型对话（流式输出）"""
        payload = {
            "model": model,
            "prompt": message,
            "stream": True
        }
        
        if context:
            payload["context"] = context
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                data = json.loads(line)
                                if "response" in data and data["response"]:
                                    # 逐个字符或词语yield输出
                                    text_chunk = data["response"]
                                    yield text_chunk
                                
                                # 检查是否完成
                                if data.get("done", False):
                                    break
                                    
                            except json.JSONDecodeError:
                                # 忽略无法解析的行
                                continue
                        
        except Exception as e:
            # 减少日志输出，只在必要时记录错误
            if not isinstance(e, (ConnectionError, TimeoutError)):
                print(f"流式对话错误: {e}")
            # 在异常情况下yield错误信息
            yield f"[错误: {str(e)}]"
    
    async def check_health(self) -> bool:
        """检查Ollama服务健康状态"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False 