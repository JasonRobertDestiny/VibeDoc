#!/bin/bash

# VibeDoc Agent启动脚本
echo "🚀 启动VibeDoc Agent..."

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js未安装，请先安装Node.js"
    exit 1
fi

# 检查Python
if ! command -v python &> /dev/null; then
    echo "❌ Python未安装，请先安装Python"
    exit 1
fi

# 安装Node.js依赖
echo "📦 安装MCP桥接服务依赖..."
cd mcp_bridge
npm install
cd ..

# 启动MCP桥接服务
echo "🌉 启动MCP桥接服务..."
cd mcp_bridge
node index.js &
MCP_PID=$!
cd ..

# 等待桥接服务启动
sleep 3

# 启动主应用
echo "🎯 启动VibeDoc Agent主应用..."
python app.py

# 清理后台进程
echo "🛑 清理后台进程..."
kill $MCP_PID 2>/dev/null
