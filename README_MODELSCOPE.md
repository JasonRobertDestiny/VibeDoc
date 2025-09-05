# VibeDoc Agent - AI开发计划生成器

## 🚀 项目简介

VibeDoc Agent是一个基于AI的智能开发计划生成器，集成了MCP (Model Context Protocol) 协议，能够获取外部知识并生成高质量的开发计划。

## ✨ 核心特性

### 🧠 AI智能生成
- 使用Qwen2.5-72B-Instruct模型
- 智能分析项目需求
- 生成详细开发计划和时间表

### 🔗 MCP外部知识集成
- 支持获取GitHub项目信息
- 集成网页内容抓取
- 使用官方@modelcontextprotocol/sdk
- Node.js桥接服务架构

### 📊 高质量输出
- Mermaid图表支持
- 甘特图时间规划
- AI编程提示词生成
- 内容质量验证和修复

### 🛠️ 技术架构
- **前端**: Gradio Web界面
- **后端**: Python + FastAPI
- **AI模型**: Silicon Flow API (Qwen2.5)
- **MCP服务**: Node.js桥接 + 官方SDK
- **部署**: Docker支持

## 🏗️ MCP服务架构

```
Python应用 --> Node.js桥接服务 --> MCP服务
    |              |                    |
 Gradio UI    官方MCP SDK        外部知识源
    |              |                    |
用户界面      端口3002            GitHub/网页等
```

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Node.js 16+
- npm 或 yarn

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd vibedocs
```

2. **安装Python依赖**
```bash
pip install -r requirements.txt
```

3. **安装Node.js桥接服务**
```bash
cd mcp_bridge
npm install
```

4. **配置环境变量**
```bash
cp .env.example .env
# 编辑.env文件，添加API密钥
```

5. **启动服务**

启动MCP桥接服务：
```bash
cd mcp_bridge
node index.js
```

启动主应用：
```bash
python app.py
```

6. **访问应用**
打开浏览器访问 `http://localhost:7860`

## 📝 使用方法

1. **输入项目创意** - 描述你的项目想法
2. **添加参考链接** - 可选添加GitHub或技术文档链接
3. **生成开发计划** - AI会结合外部知识生成详细计划
4. **导出结果** - 支持Markdown格式导出

## 🎯 MCP服务配置

### 支持的MCP服务
- **DeepWiki MCP**: 深度技术文档解析
- **Fetch MCP**: 通用网页内容获取

### 环境变量配置
```env
SILICONFLOW_API_KEY=your-api-key
DEEPWIKI_MCP_URL=https://mcp.api-inference.modelscope.net/xxx/sse
FETCH_MCP_URL=https://mcp.api-inference.modelscope.net/xxx/sse
SKIP_MCP=false
```

## 🐳 Docker部署

```bash
# 构建镜像
docker build -t vibedoc-agent .

# 运行容器
docker-compose up -d
```

## 📈 技术亮点

- ✅ **官方MCP SDK集成** - 使用最新的Model Context Protocol
- ✅ **智能内容处理** - 自动修复Mermaid语法等
- ✅ **多源知识融合** - 整合多个外部知识源
- ✅ **高质量输出** - 93分平均质量评分
- ✅ **完整的错误处理** - 健全的异常处理机制

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

本项目采用MIT许可证。
