"""
Ollama集成API路由
"""

from fastapi import APIRouter, HTTPException
from typing import List
from app.services.ollama_service import OllamaService
from app.schemas.ollama_schemas import ModelInfo, ChatRequest, ChatResponse

router = APIRouter()

@router.get("/models", response_model=List[ModelInfo])
async def get_available_models():
    """获取可用的Ollama模型列表"""
    ollama_service = OllamaService()
    try:
        models = await ollama_service.get_available_models()
        return models
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")

@router.post("/chat", response_model=ChatResponse)
async def chat_with_model(request: ChatRequest):
    """与指定模型进行对话"""
    ollama_service = OllamaService()
    try:
        response = await ollama_service.chat(
            model=request.model,
            message=request.message,
            context=request.context
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"对话失败: {str(e)}")

@router.get("/health")
async def check_ollama_health():
    """检查Ollama服务健康状态"""
    ollama_service = OllamaService()
    try:
        is_healthy = await ollama_service.check_health()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "ollama_available": is_healthy
        }
    except Exception as e:
        return {
            "status": "error", 
            "ollama_available": False,
            "error": str(e)
        } 