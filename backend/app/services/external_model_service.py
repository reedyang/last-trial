"""
外部AI模型管理服务
"""

import httpx
import time
import asyncio
from typing import List, Optional, AsyncGenerator
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from app.models.external_model import ExternalModel
from app.schemas.external_model_schemas import (
    ExternalModelCreate, 
    ExternalModelUpdate, 
    ExternalModelResponse,
    ExternalModelTest,
    ExternalModelTestResponse
)

class ExternalModelService:
    """外部AI模型管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_model(self, model_data: ExternalModelCreate) -> ExternalModelResponse:
        """创建外部模型"""
        # 检查名称是否重复
        existing = self.db.query(ExternalModel).filter(
            ExternalModel.name == model_data.name
        ).first()
        if existing:
            raise ValueError(f"模型名称 '{model_data.name}' 已存在")
        
        # 创建模型
        model = ExternalModel(
            name=model_data.name,
            api_url=model_data.api_url,
            model_id=model_data.model_id,
            api_key=model_data.api_key,
            description=model_data.description,
            is_active=model_data.is_active
        )
        
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        
        return ExternalModelResponse.model_validate(model)
    
    async def get_models(self, active_only: bool = False) -> List[ExternalModelResponse]:
        """获取外部模型列表"""
        query = self.db.query(ExternalModel)
        if active_only:
            query = query.filter(ExternalModel.is_active == True)
        
        models = query.order_by(ExternalModel.created_at.desc()).all()
        return [ExternalModelResponse.model_validate(model) for model in models]
    
    async def get_model(self, model_id: int) -> Optional[ExternalModelResponse]:
        """根据ID获取外部模型"""
        model = self.db.query(ExternalModel).filter(ExternalModel.id == model_id).first()
        if model:
            return ExternalModelResponse.model_validate(model)
        return None
    
    async def update_model(self, model_id: int, model_data: ExternalModelUpdate) -> Optional[ExternalModelResponse]:
        """更新外部模型"""
        model = self.db.query(ExternalModel).filter(ExternalModel.id == model_id).first()
        if not model:
            return None
        
        # 检查名称是否重复（排除自己）
        if model_data.name and model_data.name != model.name:
            existing = self.db.query(ExternalModel).filter(
                ExternalModel.name == model_data.name,
                ExternalModel.id != model_id
            ).first()
            if existing:
                raise ValueError(f"模型名称 '{model_data.name}' 已存在")
        
        # 更新字段
        update_data = model_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(model, field, value)
        
        # updated_at会自动更新
        self.db.commit()
        self.db.refresh(model)
        
        return ExternalModelResponse.model_validate(model)
    
    async def delete_model(self, model_id: int) -> bool:
        """删除外部模型"""
        model = self.db.query(ExternalModel).filter(ExternalModel.id == model_id).first()
        if not model:
            return False
        
        self.db.delete(model)
        self.db.commit()
        return True
    
    async def test_model(self, test_data: ExternalModelTest) -> ExternalModelTestResponse:
        """测试外部模型连接"""
        print(f"🧪 开始测试外部模型连接...")
        print(f"   API URL: {test_data.api_url}")
        print(f"   Model ID: {test_data.model_id}")
        print(f"   Has API Key: {bool(test_data.api_key)}")
        print(f"   注意: 已禁用SSL证书验证以支持企业内网环境")
        
        start_time = time.time()
        
        try:
            # 构建请求
            headers = {
                "Content-Type": "application/json"
            }
            
            if test_data.api_key is not None and test_data.api_key.strip():
                headers["Authorization"] = f"Bearer {test_data.api_key}"
            
            # 测试消息
            test_message = "Hello, this is a test message. Please respond briefly."
            
            # 构建OpenWebUI兼容的请求体
            request_body = {
                "model": test_data.model_id,
                "messages": [
                    {"role": "user", "content": test_message}
                ],
                "stream": False,
                "max_tokens": 50
            }
            
            # 发送请求 (禁用SSL验证以支持企业内网自签名证书)
            async with httpx.AsyncClient(timeout=30, verify=False) as client:
                # 直接使用提供的API URL（用户应该提供完整的端点）
                api_endpoint = test_data.api_url.rstrip('/')
                print(f"   请求端点: {api_endpoint}")
                print(f"   请求体: {request_body}")
                
                response = await client.post(
                    api_endpoint,
                    json=request_body,
                    headers=headers
                )
                
                print(f"   响应状态码: {response.status_code}")
                print(f"   响应内容: {response.text[:200]}...")
                
                response.raise_for_status()
                
                # 解析响应
                result = response.json()
                response_time = time.time() - start_time
                
                # 验证响应格式
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0].get('message', {}).get('content', '')
                    if content.strip():
                        success_response = ExternalModelTestResponse(
                            success=True,
                            message=f"连接成功！模型响应: {content[:100]}{'...' if len(content) > 100 else ''}",
                            response_time=response_time
                        )
                        print(f"✅ 测试成功: {success_response.message}")
                        return success_response
                
                return ExternalModelTestResponse(
                    success=False,
                    message="API响应格式不正确",
                    response_time=response_time,
                    error="响应中缺少有效内容"
                )
                
        except httpx.TimeoutException as e:
            error_response = ExternalModelTestResponse(
                success=False,
                message="连接超时",
                error="请求超时（30秒），请检查API地址是否正确"
            )
            print(f"❌ 测试失败 - 超时: {e}")
            return error_response
        except httpx.HTTPStatusError as e:
            error_response = ExternalModelTestResponse(
                success=False,
                message=f"HTTP错误: {e.response.status_code}",
                error=f"服务器返回错误: {e.response.text}"
            )
            print(f"❌ 测试失败 - HTTP错误: {e.response.status_code} - {e.response.text}")
            return error_response
        except httpx.ConnectError as e:
            error_response = ExternalModelTestResponse(
                success=False,
                message="连接失败",
                error="无法连接到指定的API地址，请检查URL是否正确"
            )
            print(f"❌ 测试失败 - 连接错误: {e}")
            return error_response
        except Exception as e:
            error_response = ExternalModelTestResponse(
                success=False,
                message="测试失败",
                error=f"未知错误: {str(e)}"
            )
            print(f"❌ 测试失败 - 未知错误: {e}")
            return error_response
    
    async def update_test_result(self, model_id: int, test_result: ExternalModelTestResponse):
        """更新模型的测试结果"""
        from datetime import datetime
        
        print(f"📝 更新模型 {model_id} 的测试结果...")
        model = self.db.query(ExternalModel).filter(ExternalModel.id == model_id).first()
        if model:
            # 使用字典更新避免类型错误
            update_data = {
                "last_tested": datetime.utcnow(),
                "test_status": "success" if test_result.success else "failed",
                "test_error": test_result.error if not test_result.success else None
            }
            
            print(f"   更新数据: {update_data}")
            
            for key, value in update_data.items():
                setattr(model, key, value)
                
            self.db.commit()
            self.db.refresh(model)
            
            print(f"✅ 测试结果已保存: 状态={model.test_status}, 时间={model.last_tested}")
        else:
            print(f"❌ 未找到模型 {model_id}")
    
    async def chat_with_external_model(self, model: ExternalModel, message: str) -> str:
        """与外部模型进行对话"""
        headers = {
            "Content-Type": "application/json"
        }
        
        if model.api_key is not None and model.api_key.strip():
            headers["Authorization"] = f"Bearer {model.api_key}"
        
        request_body = {
            "model": model.model_id,
            "messages": [
                {"role": "user", "content": message}
            ],
            "stream": False,
            "max_tokens": 500
        }
        
        try:
            async with httpx.AsyncClient(timeout=60, verify=False) as client:
                api_endpoint = model.api_url.rstrip('/')
                
                response = await client.post(
                    api_endpoint,
                    json=request_body,
                    headers=headers
                )
                
                response.raise_for_status()
                result = response.json()
                
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0].get('message', {}).get('content', '')
                
                raise ValueError("API响应格式不正确")
                
        except Exception as e:
            raise Exception(f"外部模型调用失败: {str(e)}")
    
    async def chat_with_external_model_stream(self, model: ExternalModel, message: str) -> AsyncGenerator[str, None]:
        """与外部模型进行流式对话"""
        headers = {
            "Content-Type": "application/json"
        }
        
        if model.api_key is not None and model.api_key.strip():
            headers["Authorization"] = f"Bearer {model.api_key}"
        
        request_body = {
            "model": model.model_id,
            "messages": [
                {"role": "user", "content": message}
            ],
            "stream": True,
            "max_tokens": 500
        }
        
        try:
            async with httpx.AsyncClient(timeout=60, verify=False) as client:
                api_endpoint = model.api_url.rstrip('/')
                
                async with client.stream(
                    "POST",
                    api_endpoint,
                    json=request_body,
                    headers=headers
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]  # 去掉 "data: " 前缀
                            if data.strip() == "[DONE]":
                                break
                            
                            try:
                                import json
                                chunk = json.loads(data)
                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    delta = chunk['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                continue
                
        except Exception as e:
            raise Exception(f"外部模型流式调用失败: {str(e)}") 