#!/usr/bin/env python3
"""
VibeDoc AI Agent 环境检查和修复脚本
专为赛道二：Agent应用开发赛道设计
"""

import sys
import subprocess
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_python_version():
    """检查Python版本"""
    logger.info("🐍 检查Python版本...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        logger.error("❌ Python版本过低，需要3.8+")
        return False
    logger.info(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
    return True

def install_requirements():
    """安装依赖包"""
    logger.info("📦 安装/更新依赖包...")
    
    requirements = [
        "gradio==5.34.1",  # 匹配魔搭空间版本
        "requests>=2.28.0", 
        # uuid和datetime是内置模块，不需要安装
    ]
    
    for req in requirements:
        try:
            logger.info(f"安装 {req}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", req, "--upgrade"])
            logger.info(f"✅ {req} 安装成功")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ {req} 安装失败: {e}")
            return False
    
    return True

def check_environment_variables():
    """检查环境变量配置"""
    logger.info("🔧 检查环境变量...")
    
    required_vars = {
        "SILICONFLOW_API_KEY": "SiliconFlow API密钥 (必需)",
    }
    
    optional_vars = {
        "DEEPWIKI_SSE_URL": "DeepWiki MCP服务URL (可选)",
        "FETCH_SSE_URL": "网页抓取MCP服务URL (可选)", 
        "DOUBAO_SSE_URL": "Doubao图像生成MCP服务URL (可选)",
        "DOUBAO_API_KEY": "Doubao API密钥 (可选)"
    }
    
    # 检查必需变量
    for var, desc in required_vars.items():
        value = os.environ.get(var)
        if not value:
            logger.warning(f"⚠️ {var} 未设置 - {desc}")
        else:
            logger.info(f"✅ {var} 已配置")
    
    # 检查可选变量
    mcp_count = 0
    for var, desc in optional_vars.items():
        value = os.environ.get(var)
        if value:
            logger.info(f"✅ {var} 已配置 - {desc}")
            if "URL" in var:
                mcp_count += 1
        else:
            logger.info(f"💡 {var} 未配置 - {desc}")
    
    logger.info(f"🔌 已配置的MCP服务数量: {mcp_count}/3")
    
    if mcp_count == 0:
        logger.warning("⚠️ 未配置任何MCP服务，Agent将以基础模式运行")
    else:
        logger.info(f"✅ 已配置 {mcp_count} 个MCP服务，Agent功能完整")

def check_app_structure():
    """检查应用文件结构"""
    logger.info("📁 检查应用文件结构...")
    
    required_files = [
        "app.py",
        "requirements.txt", 
        "README_TRACK2.md"
    ]
    
    for file in required_files:
        if os.path.exists(file):
            logger.info(f"✅ {file} 存在")
        else:
            logger.error(f"❌ {file} 缺失")
            return False
    
    return True

def test_basic_functionality():
    """测试基础功能"""
    logger.info("🧪 测试基础功能...")
    
    try:
        # 尝试导入主要模块
        import gradio as gr
        import requests
        logger.info("✅ 核心模块导入成功")
        
        # 检查app.py语法
        with open("app.py", "r", encoding="utf-8") as f:
            code = f.read()
            compile(code, "app.py", "exec")
        logger.info("✅ app.py 语法检查通过")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 功能测试失败: {e}")
        return False

def create_env_template():
    """创建环境变量模板"""
    logger.info("📝 创建环境变量配置模板...")
    
    env_template = """# VibeDoc AI Agent 环境变量配置
# 复制此文件为 .env 并填入实际值

# 必需配置
SILICONFLOW_API_KEY=your-siliconflow-api-key

# MCP服务配置 (可选，至少配置一个以体验完整功能)
DEEPWIKI_SSE_URL=http://your-deepwiki-mcp-server:port
FETCH_SSE_URL=http://your-fetch-mcp-server:port  
DOUBAO_SSE_URL=http://your-doubao-mcp-server:port
DOUBAO_API_KEY=your-doubao-api-key

# 应用配置
APP_PORT=7860
APP_HOST=0.0.0.0
"""
    
    with open(".env.template", "w", encoding="utf-8") as f:
        f.write(env_template)
    
    logger.info("✅ 环境变量模板已创建: .env.template")

def main():
    """主函数"""
    logger.info("🚀 VibeDoc AI Agent - 环境检查开始")
    logger.info("🎯 赛道二：Agent应用开发赛道")
    
    success = True
    
    # 1. 检查Python版本
    if not check_python_version():
        success = False
    
    # 2. 检查文件结构
    if not check_app_structure():
        success = False
    
    # 3. 安装依赖
    if not install_requirements():
        success = False
    
    # 4. 检查环境变量
    check_environment_variables()
    
    # 5. 测试基础功能
    if not test_basic_functionality():
        success = False
    
    # 6. 创建配置模板
    create_env_template()
    
    if success:
        logger.info("🎉 环境检查完成！Agent应用已准备就绪")
        logger.info("💡 启动命令: python app.py")
        logger.info("🌐 访问地址: http://localhost:7860")
        logger.info("📚 说明文档: README_TRACK2.md")
    else:
        logger.error("❌ 环境检查发现问题，请修复后重试")
        sys.exit(1)

if __name__ == "__main__":
    main()
