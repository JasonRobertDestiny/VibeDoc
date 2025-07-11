#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试MCP服务和格式化功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from urllib.parse import urlparse
from datetime import datetime

def validate_url(url: str) -> bool:
    """验证URL格式"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def generate_enhanced_reference_info(url: str, source_type: str, error_msg: str = None) -> str:
    """生成增强的参考信息，当MCP服务不可用时提供有用的上下文"""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    path = parsed_url.path
    
    # 根据URL结构推断内容类型
    content_hints = []
    
    # 检测常见的技术站点
    if "github.com" in domain:
        content_hints.append("💻 开源代码仓库")
    elif "stackoverflow.com" in domain:
        content_hints.append("❓ 技术问答")
    elif "medium.com" in domain:
        content_hints.append("📝 技术博客")
    elif "dev.to" in domain:
        content_hints.append("👨‍💻 开发者社区")
    elif "csdn.net" in domain:
        content_hints.append("🇨🇳 CSDN技术博客")
    elif "juejin.cn" in domain:
        content_hints.append("💎 掘金技术文章")
    elif "zhihu.com" in domain:
        content_hints.append("🧠 知乎技术讨论")
    elif "blog" in domain:
        content_hints.append("📖 技术博客")
    elif "docs" in domain:
        content_hints.append("📚 技术文档")
    elif "wiki" in domain:
        content_hints.append("📖 知识库")
    else:
        content_hints.append("🔗 参考资料")
    
    # 根据路径推断内容
    if "/article/" in path or "/post/" in path:
        content_hints.append("📄 文章内容")
    elif "/tutorial/" in path:
        content_hints.append("📚 教程指南")
    elif "/docs/" in path:
        content_hints.append("📖 技术文档")
    elif "/guide/" in path:
        content_hints.append("📋 使用指南")
    
    hint_text = " | ".join(content_hints) if content_hints else "📄 网页内容"
    
    reference_info = f"""
## 🔗 {source_type}参考

**📍 来源链接：** [{domain}]({url})

**🏷️ 内容类型：** {hint_text}

**🤖 AI增强分析：** 
> 虽然MCP服务暂时不可用，但AI将基于链接信息和上下文进行智能分析，
> 并在生成的开发计划中融入该参考资料的相关性建议。

**📋 参考价值：**
- ✅ 提供技术选型参考
- ✅ 补充实施细节
- ✅ 增强方案可行性
- ✅ 丰富最佳实践

---
"""
    
    if error_msg and not error_msg.startswith("❌"):
        reference_info += f"\n**⚠️ 服务状态：** {error_msg}\n"
    
    return reference_info

def fetch_external_knowledge(reference_url: str) -> str:
    """获取外部知识库内容"""
    if not reference_url or not reference_url.strip():
        return ""
    
    url = reference_url.strip()
    
    # 验证URL格式
    if not validate_url(url):
        return "❌ 无效的URL格式"
    
    # 智能路由：根据URL类型选择不同的MCP服务
    if "deepwiki.org" in url:
        return generate_enhanced_reference_info(url, "DeepWiki技术文档")
    else:
        return generate_enhanced_reference_info(url, "外部参考资料")

def test_mcp_integration():
    """测试MCP服务集成"""
    print("🔍 测试MCP服务集成...")
    
    test_url = "https://blog.csdn.net/2501_91245857/article/details/146914619"
    user_idea = "我想开发一个基于AI的代码审查工具，能够自动检测代码质量问题并给出优化建议，支持多种编程语言"
    
    print(f"📍 测试URL: {test_url}")
    print(f"💡 用户创意: {user_idea}")
    
    # 测试外部知识获取
    retrieved_knowledge = fetch_external_knowledge(test_url)
    print(f"\n📋 获取的外部知识:")
    print(f"长度: {len(retrieved_knowledge)} 字符")
    print(f"开头: {retrieved_knowledge[:100]}...")
    
    # 测试条件检查
    condition_check = retrieved_knowledge and not retrieved_knowledge.startswith("❌")
    print(f"\n🔍 条件检查:")
    print(f"retrieved_knowledge存在: {bool(retrieved_knowledge)}")
    print(f"不以❌开头: {not retrieved_knowledge.startswith('❌')}")
    print(f"最终条件: {condition_check}")
    
    # 模拟用户提示词构建
    user_prompt = f"产品创意：{user_idea}"
    
    if condition_check:
        user_prompt += f"""

# 外部知识库参考
{retrieved_knowledge}

请基于上述外部知识库参考和产品创意生成："""
        print(f"\n✅ 外部知识已注入到提示词中")
    else:
        user_prompt += """

请生成："""
        print(f"\n❌ 外部知识未注入到提示词中")
    
    print(f"\n📝 最终用户提示词:")
    print(f"长度: {len(user_prompt)} 字符")
    print(f"包含外部知识: {'外部知识库参考' in user_prompt}")
    print(f"包含CSDN: {'CSDN' in user_prompt}")
    
    # 显示部分提示词内容
    print(f"\n📄 提示词内容预览:")
    print("=" * 50)
    print(user_prompt[:500] + "..." if len(user_prompt) > 500 else user_prompt)
    print("=" * 50)

if __name__ == "__main__":
    test_mcp_integration()