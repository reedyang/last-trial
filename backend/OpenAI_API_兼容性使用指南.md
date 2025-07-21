# OpenAI API 兼容性使用指南

## 概述

系统现已支持两种类型的外部AI模型API：

1. **OpenAI API** - 标准的OpenAI ChatCompletion API格式
2. **OpenWebUI API** - OpenWebUI实例的API格式

## 支持的API类型

### 1. OpenAI API 兼容

**适用于：**
- 官方OpenAI API (ChatGPT)
- Ollama的OpenAI兼容端点
- 其他兼容OpenAI格式的第三方服务
- 自托管的OpenAI兼容API

**API端点格式：**
```
/v1/chat/completions
```

**示例配置：**

#### 官方OpenAI API
```
API类型: OpenAI API
API地址: https://api.openai.com/v1/chat/completions
模型ID: gpt-3.5-turbo
API密钥: sk-your-openai-api-key-here
```

#### 本地Ollama (OpenAI兼容模式)
```
API类型: OpenAI API
API地址: http://localhost:11434/v1/chat/completions
模型ID: llama3.1:latest
API密钥: (留空)
```

### 2. OpenWebUI API

**适用于：**
- OpenWebUI实例
- 其他兼容OpenWebUI格式的服务

**API端点格式：**
```
/api/chat/completions
```

**示例配置：**

#### OpenWebUI实例
```
API类型: OpenWebUI API
API地址: http://localhost:3000/api/chat/completions
模型ID: llama3.1:latest
API密钥: (可选)
```

## 配置步骤

### 1. 访问外部模型管理页面

在主页点击"可用模型"卡片中的"管理外部模型"按钮。

### 2. 添加新的外部模型

1. 点击"添加模型"按钮
2. 填写模型信息：
   - **显示名称**: 在游戏中显示的自定义名称
   - **API类型**: 选择 "OpenAI API" 或 "OpenWebUI API"
   - **API地址**: 根据API类型自动提示正确的端点格式
   - **模型ID**: 实际的模型标识符
   - **API密钥**: 如果需要认证则填写
   - **描述**: 可选的模型描述

### 3. 测试连接

配置完成后，点击"测试"按钮验证连接是否正常。

## 常见配置示例

### Ollama (OpenAI兼容)

如果你的Ollama支持OpenAI兼容API：

```
API类型: OpenAI API
API地址: http://localhost:11434/v1/chat/completions
模型ID: llama3.1:latest
API密钥: (留空)
```

### 自托管OpenAI兼容服务

```
API类型: OpenAI API
API地址: https://your-server.com/v1/chat/completions
模型ID: your-model-name
API密钥: your-api-key
```

### OpenWebUI实例

```
API类型: OpenWebUI API
API地址: http://your-openwebui.com/api/chat/completions
模型ID: available-model-id
API密钥: your-token (如果启用了认证)
```

## API端点自动处理

系统会根据选择的API类型自动处理端点：

- **OpenAI API**: 自动补全 `/v1/chat/completions`
- **OpenWebUI API**: 自动补全 `/api/chat/completions`

你可以提供基础URL，系统会自动构建完整的API端点。

## 故障排除

### 1. 连接失败

**常见原因：**
- URL格式不正确
- 服务未启动
- 网络连接问题
- SSL证书问题（已禁用验证）

**解决方案：**
- 检查API地址是否正确
- 确认服务正在运行
- 尝试在浏览器中访问API地址

### 2. 认证失败

**常见原因：**
- API密钥错误或过期
- 权限不足

**解决方案：**
- 验证API密钥是否正确
- 检查API密钥权限
- 对于不需要认证的服务，确保API密钥字段为空

### 3. 模型不存在

**常见原因：**
- 模型ID不正确
- 模型未部署

**解决方案：**
- 检查模型ID是否与服务端一致
- 确认模型已在服务端正确部署

## 技术细节

### OpenAI API 格式

请求体示例：
```json
{
  "model": "gpt-3.5-turbo",
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "stream": true,
  "max_tokens": 500,
  "temperature": 0.7
}
```

### OpenWebUI API 格式

请求体示例：
```json
{
  "model": "llama3.1:latest",
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "stream": true,
  "max_tokens": 500
}
```

### 流式输出支持

两种API类型都支持流式输出（Server-Sent Events），可以实现实时的AI对话显示。

## 安全注意事项

1. **SSL证书**: 系统已禁用SSL证书验证以支持企业内网环境
2. **API密钥**: 妥善保管API密钥，不要在公共环境中暴露
3. **网络访问**: 确保网络访问策略允许访问外部API服务

## 更新记录

- **2024-XX-XX**: 添加OpenAI API兼容性支持
- **2024-XX-XX**: 支持自动端点构建
- **2024-XX-XX**: 优化错误处理和用户体验 