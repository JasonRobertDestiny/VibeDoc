#!/usr/bin/env python3
"""
VibeDoc Agent 简化启动脚本
用于在没有完整依赖环境下测试核心MCP功能
"""

import sys
import os

# 添加项目目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_mcp_functionality():
    """测试MCP核心功能"""
    print("🚀 VibeDoc Agent - MCP功能测试")
    print("=" * 50)
    
    # 测试enhanced_mcp_client
    try:
        from enhanced_mcp_client import call_fetch_mcp_async, call_deepwiki_mcp_async
        print("✅ MCP客户端导入成功")
        
        # 测试Fetch MCP
        print("\n🧪 测试Fetch MCP...")
        result = call_fetch_mcp_async("https://example.com")
        print(f"   结果: {'✅ 成功' if result.success else '❌ 失败'}")
        print(f"   响应时间: {result.execution_time:.2f}s")
        if result.data:
            print(f"   内容长度: {len(result.data)} 字符")
        if result.error_message:
            print(f"   错误: {result.error_message}")
        
        # 测试DeepWiki MCP  
        print("\n📖 测试DeepWiki MCP...")
        result = call_deepwiki_mcp_async("https://deepwiki.org/openai/openai-python")
        print(f"   结果: {'✅ 成功' if result.success else '❌ 失败'}")
        print(f"   响应时间: {result.execution_time:.2f}s")
        if result.data:
            print(f"   内容长度: {len(result.data)} 字符")
        if result.error_message:
            print(f"   错误: {result.error_message}")
            
        print("\n🎉 MCP服务测试完成！")
        return True
        
    except Exception as e:
        print(f"❌ MCP测试失败: {str(e)}")
        return False

def check_gradio_availability():
    """检查Gradio是否可用"""
    try:
        import gradio as gr
        print("✅ Gradio可用")
        return True
    except ImportError:
        print("❌ Gradio不可用 - 需要安装: pip install gradio")
        return False

def main():
    """主函数"""
    print("🎯 VibeDoc Agent 启动检查")
    print("=" * 40)
    
    # 检查MCP功能
    mcp_ok = test_mcp_functionality()
    
    # 检查Gradio
    gradio_ok = check_gradio_availability()
    
    print("\n" + "=" * 40)
    print("📋 启动状态总结:")
    print(f"   MCP服务: {'✅ 可用' if mcp_ok else '❌ 不可用'}")
    print(f"   Gradio界面: {'✅ 可用' if gradio_ok else '❌ 不可用'}")
    
    if mcp_ok and gradio_ok:
        print("\n🚀 所有组件就绪，可以启动完整应用!")
        print("   运行: python app.py")
    elif mcp_ok:
        print("\n⚠️ MCP服务正常，但需要安装Gradio依赖")
        print("   建议: 在虚拟环境中安装完整依赖")
    else:
        print("\n❌ 核心组件不可用，请检查配置")
    
    return mcp_ok and gradio_ok

if __name__ == "__main__":
    main()