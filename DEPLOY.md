# VibeDoc 魔塔部署指南

## 🚀 部署到魔塔平台

### 前置准备

1. **注册魔塔账号**
   - 访问 [魔塔社区](https://modelscope.cn/)
   - 注册并完成实名认证

2. **获取 Silicon Flow API Key**
   - 访问 [Silicon Flow](https://siliconflow.cn/)
   - 注册并获取 API Key

### 部署步骤

#### 方式一：直接部署（推荐）

1. **创建 Space**
   ```bash
   # 在魔塔平台创建新的 Space
   # 选择 Gradio SDK
   # 设置为 Public
   ```

2. **上传代码**
   ```bash
   # 将项目代码打包上传
   # 或使用 Git 克隆
   git clone https://github.com/JasonRobertDestiny/VibeDocs.git
   ```

3. **配置环境变量**
   ```env
   SILICONFLOW_API_KEY=your_api_key_here
   ```

#### 方式二：Docker 部署

1. **构建镜像**
   ```bash
   docker build -t vibedoc .
   ```

2. **运行容器**
   ```bash
   docker run -p 3000:3000 \
     -e SILICONFLOW_API_KEY=your_api_key_here \
     vibedoc
   ```

### 环境配置

#### 必需的环境变量

| 变量名 | 描述 | 示例值 |
|--------|------|--------|
| `SILICONFLOW_API_KEY` | Silicon Flow API 密钥 | `sk-xxxxx` |
| `NODE_ENV` | 运行环境 | `production` |

#### 可选配置

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `PORT` | 服务端口 | `3000` |
| `HOST` | 服务主机 | `0.0.0.0` |

### 部署脚本

创建 `deploy.sh` 脚本：

```bash
#!/bin/bash

# 安装依赖
npm install

# 构建项目
npm run build

# 启动服务
npm start
```

### 健康检查

访问以下端点检查服务状态：

- **主页**: `/`
- **API**: `/api/auto-generate-plan`

### 故障排除

#### 常见问题

1. **API Key 错误**
   ```
   解决方案：检查环境变量配置是否正确
   ```

2. **模型不存在**
   ```
   解决方案：确认使用的模型名称是否正确
   ```

3. **端口冲突**
   ```
   解决方案：修改 PORT 环境变量
   ```

#### 日志查看

```bash
# 查看容器日志
docker logs container_name

# 查看实时日志
docker logs -f container_name
```

### 性能优化

1. **启用缓存**
   - 配置 Redis 缓存
   - 启用 Next.js 静态生成

2. **CDN 配置**
   - 配置静态资源 CDN
   - 启用 Gzip 压缩

3. **负载均衡**
   - 配置多实例部署
   - 设置健康检查

### 监控告警

1. **服务监控**
   - CPU 使用率
   - 内存使用率
   - 响应时间

2. **业务监控**
   - API 调用次数
   - 错误率统计
   - 用户访问量

### 安全配置

1. **API 限流**
   ```javascript
   // 示例：限制每分钟10次请求
   rateLimit: {
     windowMs: 60 * 1000,
     max: 10
   }
   ```

2. **CORS 配置**
   ```javascript
   // 配置允许的域名
   cors: {
     origin: ['https://your-domain.com']
   }
   ```

### 部署清单

- [ ] 代码上传完成
- [ ] 环境变量配置
- [ ] 健康检查通过
- [ ] 性能测试完成
- [ ] 监控配置完成
- [ ] 安全配置完成

---

## 📞 技术支持

如有部署问题，请提交 Issue 或联系：

- **GitHub Issues**: [项目问题追踪](https://github.com/JasonRobertDestiny/VibeDocs/issues)
- **魔塔社区**: [VibeDocs Space](https://modelscope.cn/spaces/JasonRobertDestiny/VibeDocs)
