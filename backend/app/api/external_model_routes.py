"""
外部AI模型管理API路由
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.external_model_service import ExternalModelService
from app.schemas.external_model_schemas import (
    ExternalModelCreate,
    ExternalModelUpdate,
    ExternalModelResponse,
    ExternalModelTest,
    ExternalModelTestResponse
)

router = APIRouter()

@router.post("/", response_model=ExternalModelResponse)
async def create_external_model(
    model_data: ExternalModelCreate,
    db: Session = Depends(get_db)
):
    """创建外部AI模型"""
    service = ExternalModelService(db)
    try:
        return await service.create_model(model_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建外部模型失败: {str(e)}")

@router.get("/", response_model=List[ExternalModelResponse])
async def get_external_models(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """获取外部AI模型列表"""
    service = ExternalModelService(db)
    try:
        return await service.get_models(active_only=active_only)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取外部模型列表失败: {str(e)}")

@router.get("/{model_id}", response_model=ExternalModelResponse)
async def get_external_model(
    model_id: int,
    db: Session = Depends(get_db)
):
    """根据ID获取外部AI模型"""
    service = ExternalModelService(db)
    try:
        model = await service.get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="外部模型不存在")
        return model
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取外部模型失败: {str(e)}")

@router.put("/{model_id}", response_model=ExternalModelResponse)
async def update_external_model(
    model_id: int,
    model_data: ExternalModelUpdate,
    db: Session = Depends(get_db)
):
    """更新外部AI模型"""
    service = ExternalModelService(db)
    try:
        model = await service.update_model(model_id, model_data)
        if not model:
            raise HTTPException(status_code=404, detail="外部模型不存在")
        return model
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新外部模型失败: {str(e)}")

@router.delete("/{model_id}")
async def delete_external_model(
    model_id: int,
    db: Session = Depends(get_db)
):
    """删除外部AI模型"""
    service = ExternalModelService(db)
    try:
        success = await service.delete_model(model_id)
        if not success:
            raise HTTPException(status_code=404, detail="外部模型不存在")
        return {"message": "外部模型已删除"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除外部模型失败: {str(e)}")

@router.post("/test", response_model=ExternalModelTestResponse)
async def test_external_model(
    test_data: ExternalModelTest,
    db: Session = Depends(get_db)
):
    """测试外部AI模型连接"""
    service = ExternalModelService(db)
    try:
        return await service.test_model(test_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"测试外部模型失败: {str(e)}")

@router.post("/{model_id}/test", response_model=ExternalModelTestResponse)
async def test_existing_external_model(
    model_id: int,
    db: Session = Depends(get_db)
):
    """测试已存在的外部AI模型"""
    service = ExternalModelService(db)
    try:
        model = await service.get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="外部模型不存在")
        
        test_data = ExternalModelTest(
            api_type=model.api_type,
            api_url=model.api_url,
            model_id=model.model_id,
            api_key=model.api_key
        )
        
        result = await service.test_model(test_data)
        
        # 更新测试结果到数据库
        await service.update_test_result(model_id, result)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"测试外部模型失败: {str(e)}") 