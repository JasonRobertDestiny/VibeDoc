【开源自荐】VibeDoc：AI开发计划生成器 - 60秒将创意转化为完整技术方案

## 项目介绍

**VibeDoc** 是一款AI驱动的开发计划生成器，帮助开发者、产品经理和创业者快速将产品创意转化为完整的技术方案和开发计划。

### 核心功能

1. **📋 智能开发计划生成**
   - 输入产品创意，60-180秒生成完整开发方案
   - 包含：产品概述、技术方案、开发计划、部署方案、推广策略
   - AI自动进行技术栈选型、架构设计、人力配置

2. **🤖 AI编程提示词生成**
   - 为每个功能模块生成可直接使用的AI编程提示词
   - 支持 Claude、ChatGPT、GitHub Copilot、Cursor 等主流AI工具
   - 提示词包含完整上下文、技术约束、输出要求

3. **📊 可视化图表自动生成**
   - 使用 Mermaid 自动生成系统架构图、流程图、甘特图
   - 所有图表可在浏览器中实时渲染
   - 支持明暗主题自动切换

4. **📁 多格式导出**
   - 一键导出 Markdown、Word、PDF、HTML 四种格式
   - 适配不同场景：GitHub展示、商务汇报、打印归档

### 技术亮点

- 基于 **Qwen2.5-72B-Instruct** 大模型，生成质量高
- 内置 **智能提示词优化器**，提升AI生成效果
- **内容质量验证系统**：自动修复Mermaid语法、清理虚假链接、更新过期日期
- 模块化架构：提示词优化、内容验证、导出管理各司其职

## 项目平台

- **Web应用**：基于 Gradio 5.34.1 构建的现代化界面
- **部署方式**：本地运行 / Docker 容器 / 云平台部署
- **运行环境**：Python 3.11+，跨平台支持

## 项目地址

https://github.com/JasonRobertDestiny/VibeDoc

## 使用演示

### 主界面
![VibeDoc主界面](https://raw.githubusercontent.com/JasonRobertDestiny/VibeDoc/master/image/vibedoc.png)

### AI编程提示词生成
![AI编程提示词](https://raw.githubusercontent.com/JasonRobertDestiny/VibeDoc/master/image/1.png)

### 完整方案展示
![生成示例](https://raw.githubusercontent.com/JasonRobertDestiny/VibeDoc/master/image/2.png)

### 实际生成案例

**输入：**
```
开发一个AR手语翻译应用，实时将手语翻译成语音和文字，
同时也能将语音和文字翻译成手语动作展示
```

**输出示例：** [HandVoice Development Plan](https://github.com/JasonRobertDestiny/VibeDoc/blob/master/HandVoice%20Development%20Plan.md)

生成内容包括：
- 完整技术架构（React Native + TensorFlow + ARKit/ARCore）
- 6个月开发计划，分3个阶段
- 系统架构图、开发甘特图
- 12个AI编程提示词，可直接用于开发

## 演示视频

📺 [Bilibili演示视频](https://www.bilibili.com/video/BV1ieagzQEAC/)

## 适用人群

✅ **开发者** - 快速验证技术方案、生成项目文档、学习架构设计
✅ **产品经理** - 将需求转化为技术方案、制作项目提案
✅ **创业者** - 快速验证产品创意、生成投资人方案
✅ **学生** - 学习最佳实践、准备技术面试、完成毕业设计

## 快速开始

```bash
# 克隆项目
git clone https://github.com/JasonRobertDestiny/VibeDoc.git
cd VibeDoc

# 安装依赖
pip install -r requirements.txt

# 配置 API Key（免费获取：https://siliconflow.cn）
cp .env.example .env
# 编辑 .env，填入 SILICONFLOW_API_KEY

# 运行
python app.py
# 访问 http://localhost:7860
```

## 项目特色

1. **真正实用** - 不是玩具项目，能解决实际需求
2. **开箱即用** - 配置简单，5分钟即可运行
3. **质量保证** - 内置质量评分系统，平均85分
4. **持续优化** - 活跃维护，欢迎PR和建议

---

希望这个工具能帮助更多人将创意快速变成现实！🚀
