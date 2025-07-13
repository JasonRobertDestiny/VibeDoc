# 🚀 VibeDoc 魔塔上传操作指南

## 📋 上传文件清单 (12个文件)

**核心应用文件 (必需):**
✅ app.py - 主应用文件 (已修复语法错误)
✅ config.py - 配置管理模块  
✅ mcp_manager.py - MCP服务管理器
✅ streaming_manager.py - 流式响应管理器
✅ requirements.txt - Python依赖列表

**文档和配置文件:**
✅ README.md - 项目说明文档
✅ DEPLOY.md - 详细部署指南
✅ CHECKLIST.md - 部署检查清单
✅ CLAUDE.md - 开发文档
✅ LICENSE - MIT开源许可证
✅ Dockerfile - Docker配置
✅ docker-compose.yml - Docker编排配置

## 🎯 立即上传步骤

### 第1步：打开魔塔创空间
```
🌐 访问: https://modelscope.cn/studios
👤 登录你的魔塔账号
➕ 点击 "创建创空间"
```

### 第2步：填写基本信息
```
📝 空间名称: vibedoc-ai-generator
📄 描述: VibeDoc - AI驱动的开发计划生成器，30秒将创意转化为完整开发方案
🔧 SDK: Gradio  
🐍 Python版本: 3.11
📁 应用文件: app.py
🌐 可见性: 公开
🏷️ 标签: AI,开发计划,Agent应用,MCP,Gradio
```

### 第3步：上传所有文件
**拖拽上传 (推荐):**
1. 选择上面清单中的12个文件
2. 一次性拖拽到上传区域
3. 等待上传完成

**文件上传顺序建议:**
```
1️⃣ requirements.txt (优先)
2️⃣ app.py (主文件)  
3️⃣ config.py, mcp_manager.py, streaming_manager.py
4️⃣ README.md, DEPLOY.md (文档)
5️⃣ 其他配置文件
```

### 第4步：设置环境变量
```bash
# 必填项
SILICONFLOW_API_KEY=你的API密钥
PORT=3000
NODE_ENV=production

# 可选项 (先不设置)
# DEEPWIKI_SSE_URL=
# FETCH_SSE_URL=  
# DOUBAO_SSE_URL=
```

### 第5步：启动部署
```
✅ 检查文件上传完成 (12/12)
✅ 检查环境变量设置正确
✅ 确认SDK为Gradio，Python为3.11
🚀 点击 "创建并启动"
```

## ⏱️ 部署时间预估

```
📦 依赖安装: 2-3分钟
🔧 环境配置: 30秒
🚀 应用启动: 1-2分钟
✅ 健康检查: 30秒
---
🕐 总计: 约5分钟
```

## 🧪 部署成功验证

**部署完成后，进行以下测试:**

### 1️⃣ 基础功能测试
```
🌐 访问: 创空间提供的链接
✅ 页面正常加载 (看到VibeDoc界面)
✅ 输入框可以输入文字
✅ 按钮可以点击
```

### 2️⃣ AI生成功能测试
```
📝 输入测试内容: "我想做一个在线笔记应用"
⏱️ 等待时间: 30-90秒
✅ 预期结果: 生成完整开发计划
✅ 包含: 产品规划、技术方案、部署策略
```

### 3️⃣ 下载功能测试
```
📄 点击 "下载开发计划" 按钮
✅ 成功下载 Markdown 文件
✅ 文件内容完整可读
```

## 🆘 常见问题解决

| 问题现象 | 可能原因 | 解决方案 |
|----------|----------|----------|
| 🔴 构建失败 | requirements.txt错误 | 检查文件格式 |
| 🟡 启动超时 | 依赖安装时间过长 | 等待5-10分钟 |
| 🟠 AI调用失败 | API密钥错误 | 重新设置SILICONFLOW_API_KEY |
| 🔵 页面无法访问 | 端口配置问题 | 确认PORT=3000 |
| ⚪ MCP服务报错 | 正常现象 | 不影响核心功能 |

## 📞 需要支持？

如果上传过程中遇到问题:
1. 🔍 先查看DEPLOY.md中的详细说明
2. 📋 对照CHECKLIST.md检查配置
3. 💬 在魔塔平台寻求技术支持
4. 🐛 通过GitHub Issues反馈问题

---

## 🎉 准备就绪！

**你现在需要做的就是:**
1. 📂 选择这12个文件
2. 🌐 打开 https://modelscope.cn/studios  
3. ⬆️ 按照上述步骤上传
4. ⏱️ 等待5分钟完成部署
5. 🧪 测试功能是否正常

**VibeDoc已经完全准备好上传到魔塔平台了！** 🚀