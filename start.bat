@echo off
chcp 65001 >nul

echo 🚀 启动VibeDoc Agent...

:: 检查Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js未安装，请先安装Node.js
    pause
    exit /b 1
)

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装，请先安装Python
    pause
    exit /b 1
)

:: 安装Node.js依赖
echo 📦 安装MCP桥接服务依赖...
cd mcp_bridge
call npm install
cd ..

:: 启动MCP桥接服务
echo 🌉 启动MCP桥接服务...
start /b cmd /c "cd mcp_bridge && node index.js"

:: 等待桥接服务启动
timeout /t 3 /nobreak >nul

:: 启动主应用
echo 🎯 启动VibeDoc Agent主应用...
python app.py

echo 🛑 应用已停止
pause
