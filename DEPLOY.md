# 魔塔平台部署指南

## 🚀 项目信息

- **项目类型**: Python Gradio 应用
- **SDK**: Gradio 5.34.1
- **运行时**: Python 3.11
- **端口**: 3000

## ⚙️ 环境变量配置

### 必须配置的环境变量

| 变量名 | 描述 | 示例值 | 必填 |
|--------|------|--------|------|
| `SILICONFLOW_API_KEY` | Silicon Flow API密钥 | `sk-xxxxxxxx` | ✅ |
| `PORT` | 应用端口 | `3000` | ✅ |
| `NODE_ENV` | 运行环境 | `production` | ✅ |

### 可选的MCP服务配置

| 变量名 | 描述 | 示例值 | 必填 |
|--------|------|--------|------|
| `DEEPWIKI_SSE_URL` | DeepWiki MCP服务URL | `http://localhost:8080` | ❌ |
| `FETCH_SSE_URL` | Fetch MCP服务URL | `http://localhost:8081` | ❌ |
| `DOUBAO_SSE_URL` | Doubao MCP服务URL | `http://localhost:8082` | ❌ |
| `DOUBAO_API_KEY` | Doubao API密钥 | `your-doubao-key` | ❌ |

## 📋 部署步骤

### 1. 创建创空间

1. 访问 [ModelScope创空间](https://modelscope.cn/studios)
2. 点击"创建创空间"
3. 选择 **Gradio** SDK
4. 输入项目基本信息

### 2. 配置项目

**项目配置:**
- **名称**: `VibeDoc - AI开发计划生成器`
- **描述**: `🔥 一键将创意转化为完整开发方案！AI驱动的智能开发计划生成器`
- **SDK**: `Gradio`
- **Python版本**: `3.11`
- **App文件**: `app.py`

### 3. 设置环境变量

在创空间设置中添加以下环境变量：

```bash
SILICONFLOW_API_KEY=你的API密钥
PORT=3000
NODE_ENV=production
```

### 4. 文件上传

上传以下文件到创空间：
- `app.py` - 主应用文件
- `config.py` - 配置管理
- `mcp_manager.py` - MCP服务管理器  
- `streaming_manager.py` - 流式输出管理
- `requirements.txt` - Python依赖
- `README.md` - 项目说明

### 5. 启动应用

1. 点击"构建并启动"
2. 等待依赖安装完成
3. 应用将在 `http://your-space.modelscope.cn` 可访问

## 🔧 故障排除

### 常见问题

**问题1: 应用启动失败**
- 检查 `SILICONFLOW_API_KEY` 是否正确设置
- 确认 `requirements.txt` 中的依赖版本兼容

**问题2: MCP服务连接失败**
- 这是正常现象，应用会自动降级到内置AI模式
- 不影响核心功能使用

**问题3: 端口访问问题**
- 确保 `PORT` 环境变量设置为 `3000`
- Gradio会自动处理端口绑定

## 📊 部署验证

应用启动后，检查以下功能：

1. ✅ 页面正常加载
2. ✅ 输入框接受文本输入
3. ✅ AI生成功能正常工作
4. ✅ 结果展示和下载功能正常

## 🎯 性能优化建议

1. **API配置**: 确保Silicon Flow API密钥有足够配额
2. **超时设置**: 默认120秒AI响应超时，可根据需要调整
3. **日志级别**: 生产环境建议设置 `LOG_LEVEL=WARNING`

## 🌐 访问应用

部署完成后，你的应用将在以下地址可访问：
`https://modelscope.cn/studios/你的用户名/你的空间名称`

## 🤝 技术支持

如遇部署问题，请：
1. 检查本指南的配置项
2. 查看创空间的构建日志
3. 通过GitHub Issues反馈问题