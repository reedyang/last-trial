"""
Ollama集成服务（支持外部模型）
"""

import httpx
import asyncio
import json
from typing import List, Optional, AsyncGenerator
from sqlalchemy.orm import Session
from app.core.config import settings
from app.schemas.ollama_schemas import ModelInfo, ChatResponse
from app.models.external_model import ExternalModel, APIType
from app.services.external_model_service import ExternalModelService

class OllamaService:
    """Ollama API集成服务（支持外部模型）"""
    
    def __init__(self, db: Optional[Session] = None):
        self.base_url = settings.OLLAMA_BASE_URL
        self.timeout = settings.OLLAMA_TIMEOUT
        self.db = db
        # 初始化外部模型服务
        self.external_service = ExternalModelService(db) if db else None
    
    async def get_available_models(self) -> List[ModelInfo]:
        """获取可用模型列表（包括本地和外部模型）"""
        models = []
        
        # 获取本地Ollama模型
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                
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
        except Exception as e:
            print(f"获取本地Ollama模型失败: {e}")
        
        # 获取外部模型
        if self.db:
            try:
                external_models = self.db.query(ExternalModel).filter(
                    ExternalModel.is_active.is_(True)
                ).all()
                
                for ext_model in external_models:
                    api_type_desc = "OpenAI API" if ext_model.api_type == APIType.OPENAI else "OpenWebUI API"
                    models.append(ModelInfo(
                        name=f"external:{ext_model.name}",  # 添加前缀区分外部模型
                        size=None,
                        format="external",
                        family=f"External ({api_type_desc})",
                        families=["external"],
                        parameter_size=None,
                        quantization_level=None
                    ))
            except Exception as e:
                print(f"获取外部模型失败: {e}")
        
        return models
    
    async def chat(self, model: str, message: str, context: Optional[str] = None) -> ChatResponse:
        """与模型对话（非流式）"""
        # 检查是否是外部模型
        if model.startswith("external:") and self.db:
            return await self._chat_external(model, message, context)
        
        # 使用本地Ollama模型
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
    
    async def _chat_external(self, model: str, message: str, context: Optional[str] = None) -> ChatResponse:
        """与外部模型对话"""
        if not self.db or not self.external_service:
            raise ValueError("数据库连接不可用")
            
        # 获取外部模型名称（去掉external:前缀）
        model_name = model[9:]  # 去掉 "external:" 前缀
        
        external_model = self.db.query(ExternalModel).filter(
            ExternalModel.name == model_name,
            ExternalModel.is_active.is_(True)
        ).first()
        
        if not external_model:
            raise ValueError(f"外部模型 {model_name} 不存在或未启用")
        
        # 构建消息内容
        full_message = message
        if context:
            full_message = f"Context: {context}\n\nMessage: {message}"
        
        try:
            # 使用ExternalModelService进行调用
            response_content = await self.external_service.chat_with_external_model(external_model, full_message)
            
            return ChatResponse(
                model=model,
                message=response_content,
                done=True
            )
            
        except Exception as e:
            raise ValueError(f"外部模型调用失败: {str(e)}")
    
    async def chat_stream(self, model: str, message: str, context: Optional[str] = None) -> AsyncGenerator[str, None]:
        """与模型对话（流式输出）"""
        # 检查是否是外部模型
        if model.startswith("external:") and self.db:
            async for chunk in self._chat_stream_external(model, message, context):
                yield chunk
            return
        
        # 使用本地Ollama模型
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
    
    async def _chat_stream_external(self, model: str, message: str, context: Optional[str] = None) -> AsyncGenerator[str, None]:
        """与外部模型进行流式对话"""
        if not self.db or not self.external_service:
            raise ValueError("数据库连接不可用")
            
        # 获取外部模型名称（去掉external:前缀）
        model_name = model[9:]  # 去掉 "external:" 前缀
        
        external_model = self.db.query(ExternalModel).filter(
            ExternalModel.name == model_name,
            ExternalModel.is_active.is_(True)
        ).first()
        
        if not external_model:
            raise ValueError(f"外部模型 {model_name} 不存在或未启用")
        
        # 构建消息内容
        full_message = message
        if context:
            full_message = f"Context: {context}\n\nMessage: {message}"
        
        try:
            # 使用ExternalModelService进行流式调用
            async for chunk in self.external_service.chat_with_external_model_stream(external_model, full_message):
                yield chunk
                
        except Exception as e:
            yield f"[外部模型错误: {str(e)}]" 