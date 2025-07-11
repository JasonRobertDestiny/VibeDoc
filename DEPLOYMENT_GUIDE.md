# 魔塔平台部署说明

## 🎯 项目信息

**项目名称：** VibeDoc - AI Agent开发计划生成器  
**仓库地址：** https://www.modelscope.cn/studios/JasonRobert/Vibedocs/  
**分支：** master  
**最新提交：** 🎉 重大功能优化完成：修复MCP服务集成、恢复复制按钮、优化Markdown格式

## 🚀 部署配置

### 1. 基础配置

```yaml
# 应用配置
app_file: app.py
sdk: gradio
sdk_version: 5.34.1
python_version: 3.11
```

### 2. 环境变量配置

**必填环境变量：**
```
SILICONFLOW_API_KEY=your_siliconflow_api_key_here
```

**可选环境变量（MCP服务）：**
```
DEEPWIKI_SSE_URL=http://localhost:8080
FETCH_SSE_URL=http://localhost:8081
DOUBAO_SSE_URL=http://localhost:8082
DOUBAO_API_KEY=your_doubao_api_key_here
```

**应用配置：**
```
PORT=3000
NODE_ENV=production
LOG_LEVEL=INFO
```

### 3. 完整的环境变量列表

| 变量名 | 描述 | 示例值 | 是否必填 |
|--------|------|--------|----------|
| `SILICONFLOW_API_KEY` | Silicon Flow API密钥 | `sk-xxx...` | ✅ 必填 |
| `DEEPWIKI_SSE_URL` | DeepWiki MCP服务URL | `http://localhost:8080` | ⚠️ 可选 |
| `FETCH_SSE_URL` | 通用抓取MCP服务URL | `http://localhost:8081` | ⚠️ 可选 |
| `DOUBAO_SSE_URL` | Doubao图像生成服务URL | `http://localhost:8082` | ⚠️ 可选 |
| `DOUBAO_API_KEY` | Doubao API密钥 | `your_doubao_key` | ⚠️ 可选 |
| `PORT` | 应用端口 | `3000` | ✅ 必填 |
| `NODE_ENV` | 运行环境 | `production` | ✅ 必填 |
| `LOG_LEVEL` | 日志级别 | `INFO` | ⚠️ 可选 |

## 🔧 部署步骤

### 1. 创建或更新应用

1. 登录魔塔平台
2. 进入您的创空间：https://www.modelscope.cn/studios/JasonRobert/Vibedocs/
3. 点击"设置"或"Settings"
4. 更新应用配置

### 2. 配置文件设置

确保以下文件存在且配置正确：

**app.py** - 主应用文件 ✅  
**requirements.txt** - 依赖包列表 ✅  
**README.md** - 项目说明文档 ✅  
**.env.example** - 环境变量示例 ✅  
**Dockerfile** - Docker配置 ✅  
**docker-compose.yml** - 容器编排 ✅

### 3. 环境变量设置

在魔塔平台的设置页面添加环境变量：

```bash
# 必填
SILICONFLOW_API_KEY=sk-your-actual-api-key-here

# 应用配置
PORT=3000
NODE_ENV=production
LOG_LEVEL=INFO

# 可选MCP服务（如果有的话）
# DEEPWIKI_SSE_URL=http://localhost:8080
# FETCH_SSE_URL=http://localhost:8081
# DOUBAO_SSE_URL=http://localhost:8082
# DOUBAO_API_KEY=your_doubao_api_key_here
```

### 4. 部署验证

部署完成后，验证以下功能：

- [ ] 应用正常启动
- [ ] 界面显示正常
- [ ] 输入验证工作正常
- [ ] AI生成功能正常
- [ ] 复制按钮功能正常
- [ ] 下载功能正常
- [ ] 外部链接处理正常（即使MCP服务不可用）

## 🎉 最新优化特性

### 1. 核心功能改进

- ✅ **MCP服务集成修复** - 智能处理外部链接，即使服务不可用也能提供有用信息
- ✅ **复制按钮恢复** - 兼容Gradio 5.34.1，支持复制开发计划和编程提示词
- ✅ **Markdown格式优化** - 添加层级标题、emoji图标和视觉亮点
- ✅ **参考链接智能识别** - 自动识别CSDN、GitHub、Stack Overflow等技术站点

### 2. 界面体验提升

- 🎨 **更美观的UI** - 新增CSS样式和布局优化
- 🔄 **更好的交互** - 复制按钮和状态反馈
- 📝 **更清晰的内容** - 结构化输出和视觉层次
- 🔗 **更智能的参考** - 自动生成参考信息和上下文

### 3. 技术架构改进

- 🛠️ **模块化设计** - 新增专门的函数处理不同功能
- 🔧 **完善的错误处理** - 降级机制和用户友好提示
- 📊 **可扩展性** - 易于添加新的技术站点识别规则
- 🎯 **性能优化** - 高效的文本处理和格式化

## 📱 使用指南

### 1. 基本使用流程

1. **输入产品创意** - 在主输入框中描述您的产品想法
2. **添加参考链接**（可选）- 输入相关技术文档或博客链接
3. **AI生成** - 点击生成按钮，30秒获得完整开发计划
4. **复制内容** - 使用新的复制按钮快速复制所需内容
5. **下载文档** - 导出完整的Markdown文档

### 2. 支持的参考链接类型

- 🇨🇳 **CSDN技术博客** - 如：`https://blog.csdn.net/xxx/article/details/xxx`
- 💻 **GitHub项目** - 如：`https://github.com/username/repository`
- ❓ **Stack Overflow** - 如：`https://stackoverflow.com/questions/xxx`
- 📝 **技术博客** - Medium、Dev.to等
- 💎 **掘金文章** - 如：`https://juejin.cn/post/xxx`
- 🧠 **知乎技术讨论** - 如：`https://zhihu.com/question/xxx`

### 3. 新功能体验

- 📋 **复制开发计划** - 一键复制完整的开发计划
- 🤖 **复制编程提示词** - 单独复制AI编程助手提示词
- 🎨 **美观的输出格式** - 层级标题、emoji图标、视觉分隔符
- 🔗 **智能参考处理** - 自动识别和生成参考信息

## 🔍 故障排除

### 1. 常见问题

**Q: 应用无法启动**
A: 检查环境变量配置，确保`SILICONFLOW_API_KEY`已正确设置

**Q: AI生成功能不工作**
A: 验证Silicon Flow API密钥是否有效，账户是否有足够余额

**Q: 复制按钮不工作**
A: 检查浏览器是否支持Clipboard API，尝试使用现代浏览器

**Q: 参考链接没有被处理**
A: 这是正常的，系统会在MCP服务不可用时提供智能降级处理

### 2. 日志检查

查看应用日志中的以下信息：
- MCP服务连接状态
- API调用成功/失败记录
- 错误信息和堆栈跟踪

### 3. 性能监控

关注以下指标：
- 响应时间（目标：30秒内）
- 成功率（目标：>95%）
- 用户体验反馈

## 📞 技术支持

如果遇到部署问题，请：

1. 检查环境变量配置
2. 查看应用日志
3. 参考本文档的故障排除部分
4. 联系开发者：johnrobertdestiny@gmail.com

---

**部署完成后，您的VibeDoc应用将具备完整的Agent应用体验，包括智能的MCP服务集成、美观的界面设计和便捷的交互功能！**