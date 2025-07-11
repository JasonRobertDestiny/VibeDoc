#!/bin/bash

# VibeDoc 魔塔部署脚本
# 使用方法: bash deploy.sh

echo "🚀 开始部署 VibeDoc 到魔塔平台..."

# 检查 Node.js 版本
echo "📋 检查环境..."
node --version
npm --version

# 安装依赖
echo "📦 安装依赖..."
npm ci

# 构建项目
echo "🔨 构建项目..."
npm run build

# 检查构建结果
if [ $? -eq 0 ]; then
    echo "✅ 构建成功！"
else
    echo "❌ 构建失败！"
    exit 1
fi

# 启动服务
echo "🌟 启动服务..."
npm start

echo "🎉 部署完成！访问 http://localhost:3000 查看应用"
