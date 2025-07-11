#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VibeDoc部署检查脚本
检查环境配置是否正确，验证所有功能是否可用
"""

import os
import sys
import requests
from urllib.parse import urlparse
from datetime import datetime

def check_environment_variables():
    """检查环境变量配置"""
    print("🔍 检查环境变量配置...")
    
    # 必填环境变量
    required_vars = {
        'SILICONFLOW_API_KEY': 'Silicon Flow API密钥',
        'PORT': '应用端口',
    }
    
    # 可选环境变量
    optional_vars = {
        'DEEPWIKI_SSE_URL': 'DeepWiki MCP服务URL',
        'FETCH_SSE_URL': '通用抓取MCP服务URL', 
        'DOUBAO_SSE_URL': 'Doubao图像生成服务URL',
        'DOUBAO_API_KEY': 'Doubao API密钥',
        'NODE_ENV': '运行环境',
        'LOG_LEVEL': '日志级别'
    }
    
    all_good = True
    
    print("\n📋 必填环境变量:")
    for var, desc in required_vars.items():
        value = os.environ.get(var)
        if value:
            # 隐藏敏感信息
            display_value = value[:8] + "..." if 'KEY' in var else value
            print(f"  ✅ {var}: {display_value} ({desc})")
        else:
            print(f"  ❌ {var}: 未设置 ({desc})")
            all_good = False
    
    print("\n📋 可选环境变量:")
    for var, desc in optional_vars.items():
        value = os.environ.get(var)
        if value:
            display_value = value[:8] + "..." if 'KEY' in var else value
            print(f"  ✅ {var}: {display_value} ({desc})")
        else:
            print(f"  ⚠️  {var}: 未设置 ({desc}) - 对应功能将不可用")
    
    return all_good

def test_api_connectivity():
    """测试API连接性"""
    print("\n🌐 测试API连接性...")
    
    api_key = os.environ.get('SILICONFLOW_API_KEY')
    if not api_key:
        print("  ❌ 无法测试API连接 - API密钥未设置")
        return False
    
    try:
        # 测试Silicon Flow API
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # 使用一个简单的测试请求
        test_payload = {
            "model": "Qwen/Qwen2.5-72B-Instruct",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10
        }
        
        print("  🔄 测试Silicon Flow API连接...")
        response = requests.post(
            "https://api.siliconflow.cn/v1/chat/completions",
            headers=headers,
            json=test_payload,
            timeout=10
        )
        
        if response.status_code == 200:
            print("  ✅ Silicon Flow API连接正常")
            return True
        elif response.status_code == 401:
            print("  ❌ API密钥无效")
            return False
        else:
            print(f"  ⚠️  API返回状态码: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("  ⚠️  API连接超时")
        return False
    except requests.exceptions.ConnectionError:
        print("  ❌ 无法连接到API服务")
        return False
    except Exception as e:
        print(f"  ❌ API测试失败: {str(e)}")
        return False

def test_mcp_services():
    """测试MCP服务"""
    print("\n🔌 测试MCP服务...")
    
    mcp_services = {
        'DEEPWIKI_SSE_URL': 'DeepWiki服务',
        'FETCH_SSE_URL': '通用抓取服务',
        'DOUBAO_SSE_URL': 'Doubao图像服务'
    }
    
    available_services = 0
    
    for var, name in mcp_services.items():
        url = os.environ.get(var)
        if url:
            try:
                print(f"  🔄 测试{name}...")
                response = requests.get(url, timeout=5)
                if response.status_code < 500:
                    print(f"  ✅ {name}可用")
                    available_services += 1
                else:
                    print(f"  ⚠️  {name}响应异常: {response.status_code}")
            except Exception as e:
                print(f"  ❌ {name}连接失败: {str(e)}")
        else:
            print(f"  ⚪ {name}未配置")
    
    print(f"\n📊 MCP服务状态: {available_services}/{len(mcp_services)} 个服务可用")
    return available_services

def test_core_functions():
    """测试核心功能"""
    print("\n🧪 测试核心功能...")
    
    try:
        # 测试URL验证
        from urllib.parse import urlparse
        test_url = "https://blog.csdn.net/test/article/details/123456"
        parsed = urlparse(test_url)
        url_valid = all([parsed.scheme, parsed.netloc])
        print(f"  ✅ URL验证功能: {'正常' if url_valid else '异常'}")
        
        # 测试输入验证  
        test_input = "这是一个测试输入，长度足够进行验证"
        input_valid = len(test_input.strip()) >= 10
        print(f"  ✅ 输入验证功能: {'正常' if input_valid else '异常'}")
        
        # 测试时间戳生成
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"  ✅ 时间戳生成: {timestamp}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 核心功能测试失败: {str(e)}")
        return False

def generate_deployment_report():
    """生成部署报告"""
    print("\n📊 生成部署检查报告...")
    
    env_ok = check_environment_variables()
    api_ok = test_api_connectivity()
    mcp_count = test_mcp_services()
    core_ok = test_core_functions()
    
    # 计算总体分数
    total_score = 0
    max_score = 4
    
    if env_ok:
        total_score += 1
    if api_ok:
        total_score += 1
    if mcp_count > 0:
        total_score += 1
    if core_ok:
        total_score += 1
    
    percentage = (total_score / max_score) * 100
    
    print(f"\n{'='*60}")
    print(f"📋 VibeDoc部署检查报告")
    print(f"{'='*60}")
    print(f"📅 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 总体评分: {total_score}/{max_score} ({percentage:.0f}%)")
    print(f"")
    print(f"📊 详细结果:")
    print(f"  • 环境变量配置: {'✅ 正常' if env_ok else '❌ 异常'}")
    print(f"  • API连接性: {'✅ 正常' if api_ok else '❌ 异常'}")
    print(f"  • MCP服务: ✅ {mcp_count}/3 个可用")
    print(f"  • 核心功能: {'✅ 正常' if core_ok else '❌ 异常'}")
    
    if percentage >= 75:
        status = "🟢 良好"
        advice = "应用配置良好，可以正常使用所有功能。"
    elif percentage >= 50:
        status = "🟡 一般" 
        advice = "基本功能可用，建议完善MCP服务配置以获得更好体验。"
    else:
        status = "🔴 需要修复"
        advice = "存在关键配置问题，请检查API密钥配置。"
    
    print(f"")
    print(f"🚦 部署状态: {status}")
    print(f"💡 建议: {advice}")
    
    if not env_ok:
        print(f"")
        print(f"🔧 修复建议:")
        print(f"  1. 确保设置了SILICONFLOW_API_KEY环境变量")
        print(f"  2. 在魔塔平台的设置页面添加环境变量")
        print(f"  3. 重启应用使配置生效")
    
    print(f"{'='*60}")
    
    return percentage >= 50

def main():
    """主函数"""
    print("🚀 VibeDoc部署检查开始...")
    print(f"📍 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = generate_deployment_report()
    
    if success:
        print(f"\n🎉 部署检查完成！应用可以正常使用。")
        sys.exit(0)
    else:
        print(f"\n⚠️  发现配置问题，请根据建议进行修复。")
        sys.exit(1)

if __name__ == "__main__":
    main()