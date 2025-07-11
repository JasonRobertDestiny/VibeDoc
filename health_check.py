#!/usr/bin/env python3
"""
VibeDoc健康检查脚本
用于诊断应用启动和运行问题
"""

import os
import sys
import importlib
import logging

def check_environment():
    """检查环境配置"""
    print("🔍 检查环境配置...")
    
    # 检查Python版本
    python_version = sys.version
    print(f"Python版本: {python_version}")
    
    # 检查环境变量
    api_key = os.environ.get("SILICONFLOW_API_KEY")
    mcp_server = os.environ.get("GRADIO_MCP_SERVER")
    
    print(f"SILICONFLOW_API_KEY: {'✅ 已配置' if api_key else '❌ 未配置'}")
    print(f"GRADIO_MCP_SERVER: {'✅ 已配置' if mcp_server else '⚠️ 未配置'}")
    
    return bool(api_key)

def check_dependencies():
    """检查依赖包"""
    print("\n📦 检查依赖包...")
    
    required_packages = [
        'gradio',
        'requests', 
        'pydantic',
        'uvicorn'
    ]
    
    all_ok = True
    for package in required_packages:
        try:
            module = importlib.import_module(package)
            version = getattr(module, '__version__', 'Unknown')
            print(f"{package}: ✅ {version}")
        except ImportError:
            print(f"{package}: ❌ 未安装")
            all_ok = False
    
    # 检查MCP扩展
    try:
        import gradio
        if hasattr(gradio, 'mcp'):
            print("gradio[mcp]: ✅ MCP扩展可用")
        else:
            print("gradio[mcp]: ⚠️ MCP扩展可能不可用")
    except:
        print("gradio[mcp]: ❌ MCP扩展检查失败")
        all_ok = False
    
    return all_ok

def check_app_config():
    """检查应用配置"""
    print("\n⚙️ 检查应用配置...")
    
    try:
        # 尝试导入app.py
        sys.path.insert(0, '.')
        import app
        print("app.py: ✅ 导入成功")
        
        # 检查关键函数
        if hasattr(app, 'generate_plan'):
            print("generate_plan函数: ✅ 存在")
        else:
            print("generate_plan函数: ❌ 不存在")
            return False
            
        if hasattr(app, 'demo'):
            print("Gradio demo: ✅ 存在")
        else:
            print("Gradio demo: ❌ 不存在")
            return False
        
        return True
    except Exception as e:
        print(f"app.py: ❌ 导入失败 - {e}")
        return False

def main():
    print("🚀 VibeDoc健康检查开始\n")
    
    env_ok = check_environment()
    deps_ok = check_dependencies()
    app_ok = check_app_config()
    
    print("\n📊 检查结果汇总:")
    print(f"环境配置: {'✅' if env_ok else '❌'}")
    print(f"依赖包: {'✅' if deps_ok else '❌'}")
    print(f"应用配置: {'✅' if app_ok else '❌'}")
    
    if env_ok and deps_ok and app_ok:
        print("\n🎉 所有检查通过，应用应该可以正常运行！")
        return 0
    else:
        print("\n⚠️ 发现问题，请根据上述信息进行修复")
        return 1

if __name__ == "__main__":
    exit(main())
