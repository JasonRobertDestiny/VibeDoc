# 🚀 VibeDoc：您的随身AI产品经理与架构师

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Gradio](https://img.shields.io/badge/Gradio-5.34.1-orange)](https://gradio.app/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

<div align="center">

**60-180秒，将创意转化为完整开发方案**

您的随身AI产品经理与架构师，智能生成技术文档、架构图表和AI编程提示词

[🌐 在线体验](https://modelscope.cn/studios/JasonRobert/Vibedocs) | [🎬 演示视频](https://www.bilibili.com/video/BV1ieagzQEAC/) | [🤝 参与贡献](./CONTRIBUTING.md) | [💬 讨论社区](https://github.com/JasonRobertDestiny/VibeDoc/discussions) | [English](./README.md)

</div>

---

## ✨ 为什么选择 VibeDoc？

作为开发者、产品经理或创业者，您是否遇到过这些问题：

- 💭 **有好创意，不知如何规划？** 想法很多，但不知道如何转化为可执行的开发计划
- ⏰ **文档编写耗时太长？** 写技术方案、架构文档要花费大量时间
- 🤖 **AI工具不会用？** 想用AI辅助编程，但不知道如何写好提示词
- 📊 **缺少专业图表？** 需要架构图、流程图、甘特图，但不熟悉画图工具

**VibeDoc 一站式解决！**

![VibeDoc主界面](./image/vibedoc.png)

## 🎯 核心功能

### 📋 智能开发计划生成

输入产品创意，AI在60-180秒内自动生成完整开发计划：

- **产品概述** - 项目背景、目标用户、核心价值
- **技术方案** - 技术栈选型、架构设计、技术对比
- **开发计划** - 分阶段实施计划、时间安排、人力配置
- **部署方案** - 环境配置、CI/CD流程、运维监控
- **推广策略** - 市场定位、运营建议、增长策略

### 🤖 AI编程提示词生成

为每个功能模块生成可直接使用的AI编程提示词，支持：

- ✅ **Claude** - 代码生成、架构设计
- ✅ **GitHub Copilot** - 智能代码补全
- ✅ **ChatGPT** - 技术咨询、代码优化
- ✅ **Cursor** - AI辅助编程

![AI编程提示词](./image/1.png)

### 📊 可视化图表自动生成

使用 Mermaid 自动生成专业图表：

- 🏗️ **系统架构图** - 清晰展示系统组件关系
- 📈 **业务流程图** - 可视化业务逻辑
- 📅 **甘特图** - 项目时间规划一目了然
- 📊 **技术对比表** - 技术选型决策参考

### 📁 多格式文档导出

一键导出，满足不同场景需求：

- **Markdown** (.md) - 适合版本控制、GitHub展示
- **Word** (.docx) - 商务文档、项目汇报
- **PDF** (.pdf) - 正式提案、打印归档
- **HTML** (.html) - 网页展示、在线分享

![生成示例](./image/2.png)

## 💡 真实案例展示

### 输入创意
```
开发一款AR手语翻译应用，能够实时将手语翻译成语音和文字，
同时也能将语音和文字翻译成手语动作，以AR形式展示
```

### 生成结果

**📄 [查看完整开发计划](./HandVoice_Development_Plan.md)** (1万+字)

AI生成的完整方案包括：

#### 1. **产品概述**
- 目标用户（聋哑人群、医疗工作者、教育工作者）
- 核心功能（实时翻译、多语言支持、AR可视化）
- 市场定位和竞品分析

#### 2. **技术架构**
完整的系统架构图，包括：
- 用户界面组件
- 后端服务
- 机器学习模型集成
- 数据库设计
- AR渲染管线

#### 3. **技术栈**
- **前端**：React Native（跨平台）
- **后端**：Node.js + Express
- **机器学习**：TensorFlow 手语识别模型
- **自然语言处理**：spaCy
- **AR显示**：ARKit (iOS) / ARCore (Android)
- **数据库**：MongoDB

#### 4. **开发时间表**
6个月计划，分3个主要里程碑：
- **第1-2月**：核心识别与翻译引擎
- **第3-4月**：AR集成与UI开发
- **第5-6月**：测试、优化与部署

#### 5. **12+个AI编程提示词**
每个功能模块的ready-to-use提示词。示例：

```
功能：手势识别模型

上下文：
构建实时手势识别系统用于手语翻译。
需要检测和分类手部位置、动作和面部表情。

需求：
- 处理30+ FPS的视频帧
- 识别500+种手语手势
- 支持连续手势序列
- 处理不同光照条件

技术栈：
- TensorFlow/Keras 模型训练
- MediaPipe 手部关键点检测
- OpenCV 图像预处理

约束条件：
- 必须在移动设备运行 (iOS/Android)
- 模型大小 < 50MB 用于移动部署
- 推理时间 < 100ms 每帧

期望输出：
- 模型架构代码
- 训练管道
- 数据预处理函数
- 移动端优化策略
```

## 🚀 快速开始

### 🌐 在线体验（推荐）

**👉 [立即体验 VibeDoc](https://modelscope.cn/studios/JasonRobert/Vibedocs)** - 无需安装，打开即用！

体验完整功能：
1. 输入您的产品创意（例如："开发一个智能健身APP"）
2. 可选填写参考链接（帮助AI获取更多上下文）
3. 点击生成，等待60-180秒
4. 查看完整开发方案和AI编程提示词
5. 一键导出为Markdown/Word/PDF/HTML格式

### 💻 本地部署

#### 环境要求

- Python 3.11+
- pip 包管理器
- [SiliconFlow API Key](https://siliconflow.cn) (免费获取)

#### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/JasonRobertDestiny/VibeDoc.git
cd VibeDoc

# 2. 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，添加你的 API Key
```

### 配置说明

在 `.env` 文件中配置：

```env
# 必填：SiliconFlow API Key（免费注册获取）
SILICONFLOW_API_KEY=your_api_key_here

# 可选：高级配置
API_TIMEOUT=300
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### 运行应用

```bash
python app.py
```

应用将在以下地址启动：
- 本地访问: http://localhost:7860
- 网络访问: http://0.0.0.0:7860

### 🐳 Docker 部署（可选）

```bash
# 构建镜像
docker build -t vibedoc .

# 运行容器
docker run -p 7860:7860 \
  -e SILICONFLOW_API_KEY=your_key \
  vibedoc
```

## 🏗️ 技术架构

VibeDoc 采用模块化架构设计：

```
┌─────────────────────────────────────────┐
│         Gradio Web Interface            │
│  (用户交互 + UI渲染 + 文件导出)           │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       核心处理引擎 (app.py)              │
├─────────────────────────────────────────┤
│  • 输入验证与优化                        │
│  • AI生成协调                           │
│  • 内容质量控制                          │
│  • 多格式导出                            │
└──┬────────┬──────────┬─────────┬────────┘
   │        │          │         │
   ▼        ▼          ▼         ▼
┌──────┐ ┌────────┐ ┌──────┐ ┌──────────┐
│AI模型│ │提示词  │ │内容  │ │导出      │
│集成  │ │优化器  │ │验证  │ │管理器    │
└──────┘ └────────┘ └──────┘ └──────────┘
```

### 核心技术栈

- **前端界面**: Gradio 5.34.1 - 快速构建AI应用界面
- **AI模型**: Qwen2.5-72B-Instruct - 阿里云通义千问大模型
- **图表渲染**: Mermaid.js - 代码化生成专业图表
- **文档导出**: python-docx, reportlab - 多格式支持
- **异步处理**: asyncio, aiofiles - 高性能异步处理

## 📊 性能指标

| 指标 | 表现 |
|------|------|
| **生成速度** | 60-180秒完成完整方案 |
| **成功率** | >95% 生成成功率 |
| **内容质量** | 平均质量分 85/100 |
| **支持格式** | 4种专业文档格式 |

## 🎨 使用场景

### 👨‍💻 开发者
- ✅ 快速验证技术方案可行性
- ✅ 生成项目技术文档
- ✅ 获取AI编程辅助提示词
- ✅ 学习最佳架构实践

### 📊 产品经理
- ✅ 将需求转化为技术方案
- ✅ 生成项目规划文档
- ✅ 估算开发周期和资源
- ✅ 制作项目提案PPT

### 🎓 学生 & 学习者
- ✅ 学习软件开发最佳实践
- ✅ 了解技术架构设计
- ✅ 准备技术面试
- ✅ 完成毕业设计规划

### 🚀 创业者
- ✅ 快速验证产品创意
- ✅ 生成技术方案给投资人
- ✅ 规划MVP开发路线
- ✅ 评估技术实现成本

## 🤝 参与贡献

我们欢迎所有形式的贡献！无论是：

- 🐛 报告 Bug
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码

### 贡献步骤

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

详细指南请查看 [CONTRIBUTING.md](./CONTRIBUTING.md)

## 💬 加入社区

欢迎加入 VibeDoc 交流群，与其他用户和开发者交流经验、分享创意！

<div align="center">
<img src="./image/discussion_group.jpg" width="300" alt="VibeDoc交流群二维码">

**扫码加入 VibeDoc 交流群**

分享使用经验 | 获取技术支持 | 参与产品讨论
</div>

## 📝 开发文档

- [用户指南](./USER_GUIDE.md) - 详细使用说明
- [技术文档](./CLAUDE.md) - 代码架构和开发指南
- [部署指南](./DEPLOYMENT.md) - 生产环境部署
- [安全策略](./SECURITY.md) - 安全最佳实践

## 🎯 路线图

### v2.1 (计划中)
- [ ] 支持更多AI模型（GPT-4, Claude等）
- [ ] 团队协作功能
- [ ] 方案版本管理
- [ ] 在线编辑器

### v2.2 (计划中)
- [ ] 移动端适配
- [ ] 多语言支持（英文、日文）
- [ ] 模板市场
- [ ] API接口

## 🙏 致谢

- **Qwen2.5-72B-Instruct** by Alibaba Cloud - 强大的AI能力
- **Gradio** - 优秀的Web框架
- **SiliconFlow** - 稳定的API服务
- 所有贡献者和用户 ❤️

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 开源协议

## 📞 联系方式

- **问题反馈**: [GitHub Issues](https://github.com/JasonRobertDestiny/VibeDoc/issues)
- **讨论交流**: [GitHub Discussions](https://github.com/JasonRobertDestiny/VibeDoc/discussions)
- **邮箱**: johnrobertdestiny@gmail.com
- **演示视频**: [Bilibili](https://www.bilibili.com/video/BV1ieagzQEAC/)

## ⭐ Star History

如果这个项目对您有帮助，请给我们一个 Star ⭐！

[![Star History Chart](https://api.star-history.com/svg?repos=JasonRobertDestiny/VibeDoc&type=Date)](https://star-history.com/#JasonRobertDestiny/VibeDoc&Date)

---

<div align="center">

**🚀 用AI赋能每一个创意**

Made with ❤️ by the VibeDoc Team

</div>
