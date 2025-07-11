# 贡献指南

感谢您对 VibeDoc 项目的关注！我们欢迎各种形式的贡献，包括但不限于：

- 🐛 报告 Bug
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码修复
- ✨ 开发新功能

## 🚀 快速开始

### 环境准备

确保您的开发环境满足以下要求：

- Node.js 18+ 
- Git
- 您喜欢的代码编辑器（推荐 VS Code）

### 本地开发

1. **Fork 项目**
   
   点击页面右上角的 "Fork" 按钮

2. **克隆到本地**
   ```bash
   git clone https://github.com/YOUR_USERNAME/VibeDocs.git
   cd VibeDocs
   ```

3. **安装依赖**
   ```bash
   npm install
   ```

4. **配置环境变量**
   ```bash
   cp .env.local.example .env.local
   # 编辑 .env.local 文件，添加您的 API Key
   ```

5. **启动开发服务器**
   ```bash
   npm run dev
   ```

## 📋 开发规范

### 代码风格

- 使用 TypeScript 进行开发
- 遵循 ESLint 规则
- 使用 Prettier 格式化代码
- 组件使用函数式组件 + Hooks
- 遵循 React 最佳实践

### 提交规范

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### 提交类型

- `feat`: 新功能
- `fix`: 问题修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构（不是新功能，也不是修复）
- `perf`: 性能优化
- `test`: 增加测试
- `chore`: 构建过程或工具变动

#### 示例

```bash
feat: 添加AI模型切换功能
fix: 修复手动填写模式返回按钮问题
docs: 更新API文档
style: 优化代码格式
```

### 分支策略

- `main`: 主分支，保持稳定
- `develop`: 开发分支
- `feature/*`: 功能分支
- `fix/*`: 修复分支
- `docs/*`: 文档分支

## 🐛 报告问题

在报告问题之前，请先检查：

1. 是否已有相似的 issue
2. 是否为已知问题
3. 是否可重现

### 问题模板

请提供以下信息：

- **问题描述**：清晰描述遇到的问题
- **重现步骤**：详细的操作步骤
- **预期行为**：您期望的结果
- **实际行为**：实际发生的情况
- **环境信息**：操作系统、浏览器、Node.js 版本等
- **截图**：如果有助于说明问题

## 💡 功能建议

我们欢迎您提出新功能建议！请提供：

- **功能描述**：详细说明建议的功能
- **使用场景**：什么情况下会用到这个功能
- **预期效果**：这个功能能解决什么问题
- **实现建议**：如果有技术实现想法

## 🔧 贡献代码

### Pull Request 流程

1. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **开发功能**
   - 编写代码
   - 添加测试（如果适用）
   - 更新文档

3. **测试验证**
   ```bash
   npm run lint    # 检查代码规范
   npm run build   # 确保构建成功
   ```

4. **提交代码**
   ```bash
   git add .
   git commit -m "feat: 添加新功能描述"
   git push origin feature/your-feature-name
   ```

5. **创建 Pull Request**
   - 提供清晰的标题和描述
   - 引用相关的 issue
   - 添加必要的截图或演示

### PR 检查清单

在提交 PR 之前，请确保：

- [ ] 代码遵循项目规范
- [ ] 没有 TypeScript 错误
- [ ] 没有 ESLint 警告
- [ ] 构建成功
- [ ] 功能测试通过
- [ ] 文档已更新（如果需要）
- [ ] 提交信息清晰

## 📚 文档贡献

文档是项目的重要组成部分，我们欢迎您：

- 修复文档中的错误
- 改进文档的表达
- 添加使用示例
- 翻译文档

## 🎯 开发重点

当前项目的开发重点：

### 短期目标
- 优化 AI 生成质量
- 改进用户界面体验
- 增加更多模板
- 完善错误处理

### 长期规划
- 支持多种 AI 模型
- 添加项目管理功能
- 集成更多开发工具
- 支持团队协作

## 🏆 贡献者

感谢所有为项目做出贡献的开发者！

<!-- 这里会自动展示贡献者头像 -->

## 💬 社区

- **GitHub Issues**: 报告问题和功能建议
- **Discussions**: 参与讨论和交流

## 📄 许可证

通过贡献代码，您同意您的贡献将在 [MIT License](LICENSE) 下许可。

---

再次感谢您的贡献！每一个贡献都让 VibeDoc 变得更好。
