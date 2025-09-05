# 🚀 ModelSpace (魔塔) 部署指南

## 📋 必要环境变量配置

在ModelSpace Space设置中，需要配置以下环境变量：

### 🔑 必填配置

| 环境变量名 | 值 | 说明 |
|-----------|-----|------|
| `SILICONFLOW_API_KEY` | `sk-xxx...` | Silicon Flow API密钥，用于AI模型调用 |
| `ENVIRONMENT` | `production` | 运行环境 |
| `PORT` | `7860` | 应用端口（ModelSpace会自动处理） |

### 🔌 MCP服务配置（可选）

| 环境变量名 | 值 | 说明 |
|-----------|-----|------|
| `DEEPWIKI_MCP_URL` | `https://mcp.api-inference.modelscope.net/xxx/sse` | DeepWiki MCP服务地址 |
| `FETCH_MCP_URL` | `https://mcp.api-inference.modelscope.net/xxx/sse` | Fetch MCP服务地址 |
| `SKIP_MCP` | `false` | 是否跳过MCP服务（true/false） |

## 🛠️ ModelSpace部署步骤

### 1. 创建Space
1. 登录 [ModelScope](https://modelscope.cn)
2. 点击"创建Space"
3. 选择"Gradio"类型
4. 填写Space信息

### 2. 上传代码
选择以下方式之一：

**方式A: Git推送**
```bash
git clone https://www.modelscope.cn/studios/your-username/your-space.git
cd your-space
# 复制项目文件
git add .
git commit -m "Initial commit"
git push origin master
```

**方式B: 文件上传**
- 直接上传项目zip文件
- 或拖拽文件夹到Space

### 3. 配置环境变量
1. 进入Space设置页面
2. 点击"Environment Variables"
3. 添加必要的环境变量：

```
SILICONFLOW_API_KEY = sk-xxx...
ENVIRONMENT = production
SKIP_MCP = false
```

### 4. 启动服务
- ModelSpace会自动检测`app.py`
- 自动安装`requirements.txt`中的依赖
- 启动Gradio应用

## 🏗️ 特殊配置说明

### Node.js依赖处理
由于MCP桥接服务需要Node.js，在ModelSpace中需要：

1. **添加启动脚本**（已包含在项目中）：
   - `start.sh` - Linux启动脚本
   - `start.bat` - Windows启动脚本

2. **修改启动方式**（如果需要）：
   在app.py中自动处理Node.js桥接服务启动

### MCP服务降级处理
如果MCP服务不可用，应用会自动：
- 跳过MCP调用
- 使用纯AI生成模式
- 提供高质量的开发计划

## 🔧 故障排除

### 常见问题

1. **API密钥错误**
   - 检查`SILICONFLOW_API_KEY`是否正确设置
   - 确认密钥有效且有足够额度

2. **MCP服务不可用**
   - 设置`SKIP_MCP=true`暂时禁用
   - 检查MCP服务URL是否正确

3. **端口冲突**
   - ModelSpace会自动处理端口
   - 无需手动修改端口配置

4. **依赖安装失败**
   - 检查`requirements.txt`是否完整
   - 确认Python版本兼容性

### 日志查看
在ModelSpace控制台中查看：
- 应用启动日志
- MCP服务调用日志
- 错误信息和堆栈跟踪

## 📈 性能优化

### 生产环境建议
1. 设置`ENVIRONMENT=production`
2. 启用MCP服务获得更好效果
3. 定期检查API密钥额度
4. 监控应用性能指标

### 成本控制
- Silicon Flow API按使用量计费
- 可通过设置合理的超时时间控制成本
- 建议开启请求限制和缓存

## 🎯 演示准备

为评委演示准备：
1. 确保API密钥有足够额度
2. 测试MCP服务正常工作
3. 准备示例项目创意和参考链接
4. 验证生成的开发计划质量

## 📞 技术支持

如有问题，可以：
1. 查看项目README
2. 检查GitHub Issues
3. 联系开发团队
