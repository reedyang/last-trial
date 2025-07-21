#!/usr/bin/env python3
"""
测试OpenAI API兼容模型的集成
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.external_model_service import ExternalModelService
from app.schemas.external_model_schemas import ExternalModelTest, APIType
from app.core.database import get_db

async def test_openai_api():
    """测试OpenAI API兼容性"""
    
    print("🧪 测试OpenAI API兼容性...")
    
    # 获取数据库会话
    db = next(get_db())
    service = ExternalModelService(db)
    
    # 测试数据
    test_configs = [
        {
            "name": "OpenAI API (example)",
            "api_type": APIType.OPENAI,
            "api_url": "https://api.openai.com/v1/chat/completions",
            "model_id": "gpt-3.5-turbo",
            "api_key": "your-openai-api-key-here"
        },
        {
            "name": "Local Ollama with OpenAI API",
            "api_type": APIType.OPENAI,
            "api_url": "http://localhost:11434/v1/chat/completions",
            "model_id": "llama3.1:latest",
            "api_key": None
        },
        {
            "name": "OpenWebUI API (example)",
            "api_type": APIType.OPENWEBUI,
            "api_url": "http://localhost:3000/api/chat/completions",
            "model_id": "llama3.1:latest",
            "api_key": None
        }
    ]
    
    for config in test_configs:
        print(f"\n📡 测试配置: {config['name']}")
        print(f"   API类型: {config['api_type'].value}")
        print(f"   API地址: {config['api_url']}")
        print(f"   模型ID: {config['model_id']}")
        print(f"   需要API密钥: {'是' if config['api_key'] else '否'}")
        
        # 构建测试请求
        test_request = ExternalModelTest(
            api_type=config['api_type'],
            api_url=config['api_url'],
            model_id=config['model_id'],
            api_key=config['api_key']
        )
        
        try:
            # 执行测试
            result = await service.test_model(test_request)
            
            if result.success:
                print(f"   ✅ 测试成功: {result.message}")
                if result.response_time:
                    print(f"   ⏱️ 响应时间: {result.response_time:.2f}秒")
            else:
                print(f"   ❌ 测试失败: {result.message}")
                if result.error:
                    print(f"   🔍 错误详情: {result.error}")
                    
        except Exception as e:
            print(f"   💥 测试异常: {str(e)}")
    
    print("\n🎯 API兼容性验证:")
    print("1. OpenAI API: 标准的ChatGPT API格式")
    print("   - 端点: /v1/chat/completions")
    print("   - 认证: Bearer token")
    print("   - 格式: standard OpenAI ChatCompletion")
    print("   - 示例: https://api.openai.com/v1/chat/completions")
    print("   - 示例: http://localhost:11434/v1/chat/completions (Ollama)")
    
    print("\n2. OpenWebUI API: OpenWebUI实例的API格式")
    print("   - 端点: /api/chat/completions")
    print("   - 认证: Bearer token (可选)")
    print("   - 格式: OpenWebUI compatible")
    print("   - 示例: http://localhost:3000/api/chat/completions")
    
    print("\n✨ 使用说明:")
    print("- 在外部模型管理页面选择正确的API类型")
    print("- OpenAI API类型支持:")
    print("  • 官方OpenAI API")
    print("  • 任何OpenAI兼容的API (如Ollama的OpenAI兼容端点)")
    print("  • 其他兼容OpenAI格式的第三方服务")
    print("- OpenWebUI API类型支持:")
    print("  • OpenWebUI实例")
    print("  • 其他兼容OpenWebUI格式的服务")
    
    db.close()

if __name__ == "__main__":
    asyncio.run(test_openai_api()) 