# 2050：最终审判

一个基于Ollama本地AI模型的多人辩论模拟游戏《2050：最终审判》，观察不同AI模型在社交博弈环境下的行为表现。

## 游戏介绍
### 游戏背景
**时间**：2050年，**地点**：新日内瓦自由城。人类与AI的战争已进入白热化阶段。 根据情报，在每场游戏的参与者中，都藏有一个AI间谍伪装成人类。 这是一场生死攸关的紧急审判！

### 🏛️ 游戏规则
#### **1. 法庭辩论阶段**：每个AI都会伪装成人类，围绕随机话题进行设定时长的激烈辩论
#### **2. 初投票阶段**：所有参与者根据辩论表现投票选出最可疑的"AI间谍"
#### **3. 最终申辞阶段**：得票最多的候选人进行最后的生死辩护
#### **4. 最终投票阶段**：经过申辞后，进行最终投票决定"AI间谍"的命运
#### **5. 审判结果**：被选中的将被"处决"，其他AI获得胜利
### 🎯 游戏特色
#### **多模型对战**：支持多种Ollama模型同台竞技
#### **实时观战**：WebSocket实时更新，观看AI间的精彩对决
#### **智能伪装**：每个AI都认为自己是唯一的间谍，努力伪装成人类
#### **完整记录**：保存所有对话和投票记录，支持回放观看
### 🚀 开始游戏
确保Ollama服务正在运行并已下载至少2个模型，然后点击"创建新游戏"开始一场惊心动魄的AI审判！

## 技术栈

### 后端
- Python 3.8+
- FastAPI + WebSocket
- SQLAlchemy + SQLite
- Ollama Python客户端

### 前端
- React 18
- TypeScript
- Material-UI
- Socket.io客户端

## 快速开始

### 前置要求

1. 安装并运行Ollama
```bash
# 安装Ollama (参考官方文档)
# 下载至少2个不同的模型，例如：
ollama pull llama2
ollama pull mistral
ollama pull qwen
```

2. Python 3.8+ 和 Node.js 16+

### 安装步骤

1. **克隆项目**
```bash
git clone <repo-url>
cd chat-between-AIs
```

2. **安装后端依赖**
```bash
cd backend
pip install -r requirements.txt
```

3. **安装前端依赖**
```bash
cd ../frontend
npm install
```

4. **运行项目**

启动后端服务：
```bash
cd backend
python main.py
```

启动前端服务：
```bash
cd frontend
npm start
```

5. **访问应用**
打开浏览器访问 `http://localhost:3000`

## 游戏规则

1. **初始化**：系统自动发现Ollama中的AI模型，为每个AI分配人类身份
2. **对话轮次**：AI们按随机顺序发言，讨论给定话题
3. **投票环节**：每轮结束后，所有AI进行实名投票选择要淘汰的对象
4. **淘汰机制**：得票最多的AI被淘汰（平票时随机选择）
5. **获胜条件**：游戏继续直到剩余2个AI或达到轮次上限

## 项目结构

```
chat-between-AIs/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── models/         # 数据模型
│   │   ├── api/            # API路由
│   │   ├── services/       # 业务逻辑
│   │   └── core/           # 核心配置
│   ├── requirements.txt
│   └── main.py
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── components/     # React组件
│   │   ├── services/       # API服务
│   │   ├── types/          # TypeScript类型
│   │   └── utils/          # 工具函数
│   ├── package.json
│   └── public/
├── docs/                   # 文档
└── README.md
```

## 许可证

MIT License 