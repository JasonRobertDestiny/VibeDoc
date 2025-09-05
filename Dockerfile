# VibeDoc Agent应用 - Docker配置
# 为魔塔MCP&Agent挑战赛2025优化
FROM python:3.11-slim

# Agent应用标签
LABEL name="VibeDoc Agent Application"
LABEL description="智能Agent开发计划生成器 - MCP多服务协作"
LABEL version="1.0.0"
LABEL competition="魔塔MCP&Agent挑战赛2025"

# 设置工作目录
WORKDIR /app

# Agent应用环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV AGENT_APP_MODE=production
ENV MCP_SERVICES_ENABLED=true

# 安装系统依赖（包含Node.js）
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ca-certificates \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_18.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 安装MCP桥接服务Node.js依赖
RUN cd mcp_bridge && npm install

# 创建非root用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 3000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# 启动命令
CMD ["python", "app.py"]