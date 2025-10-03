import gradio as gr
import requests
import os
import logging
import json
import tempfile
import re
import html
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List
from urllib.parse import urlparse

# 导入模块化组件
from config import config
# 已移除 mcp_direct_client，使用 enhanced_mcp_client
from export_manager import export_manager
from prompt_optimizer import prompt_optimizer
from explanation_manager import explanation_manager, ProcessingStage
# from plan_editor import plan_editor  # Removed - editing feature disabled

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format=config.log_format
)
logger = logging.getLogger(__name__)

# API配置
API_KEY = config.ai_model.api_key
API_URL = config.ai_model.api_url

# 应用启动时的初始化
logger.info("🚀 VibeDoc：您的随身AI产品经理与架构师")
logger.info("📦 Version: 2.0.0 | Open Source Edition")
logger.info(f"📊 Configuration: {json.dumps(config.get_config_summary(), ensure_ascii=False, indent=2)}")

# 验证配置
config_errors = config.validate_config()
if config_errors:
    for key, error in config_errors.items():
        logger.warning(f"⚠️ Configuration Warning {key}: {error}")

def get_processing_explanation() -> str:
    """获取处理过程的详细说明"""
    return explanation_manager.get_processing_explanation()

def show_explanation() -> Tuple[str, str, str]:
    """显示处理过程说明"""
    explanation = get_processing_explanation()
    return (
        gr.update(visible=False),  # 隐藏plan_output
        gr.update(value=explanation, visible=True),  # 显示process_explanation
        gr.update(visible=True)   # 显示hide_explanation_btn
    )

def hide_explanation() -> Tuple[str, str, str]:
    """隐藏处理过程说明"""
    return (
        gr.update(visible=True),   # 显示plan_output
        gr.update(visible=False),  # 隐藏process_explanation
        gr.update(visible=False)   # 隐藏hide_explanation_btn
    )

def optimize_user_idea(user_idea: str) -> Tuple[str, str]:
    """
    优化用户输入的创意描述
    
    Args:
        user_idea: 用户原始输入
        
    Returns:
        Tuple[str, str]: (优化后的描述, 优化信息)
    """
    if not user_idea or not user_idea.strip():
        return "", "❌ 请先输入您的产品创意！"
    
    # 调用提示词优化器
    success, optimized_idea, suggestions = prompt_optimizer.optimize_user_input(user_idea)
    
    if success:
        optimization_info = f"""
## ✨ 创意优化成功！

**🎯 优化建议：**
{suggestions}

**💡 提示：** 优化后的描述更加详细和专业，将帮助生成更高质量的开发计划。您可以：
- 直接使用优化后的描述生成计划
- 根据需要手动调整优化结果
- 点击"重新优化"获得不同的优化建议
"""
        return optimized_idea, optimization_info
    else:
        return user_idea, f"⚠️ 优化失败：{suggestions}"

def validate_input(user_idea: str) -> Tuple[bool, str]:
    """验证用户输入"""
    if not user_idea or not user_idea.strip():
        return False, "❌ 请输入您的产品创意！"
    
    if len(user_idea.strip()) < 10:
        return False, "❌ 产品创意描述太短，请提供更详细的信息"
    
    return True, ""

def validate_url(url: str) -> bool:
    """验证URL格式"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def fetch_knowledge_from_url_via_mcp(url: str) -> tuple[bool, str]:
    """通过增强版异步MCP服务从URL获取知识"""
    from enhanced_mcp_client import call_fetch_mcp_async, call_deepwiki_mcp_async
    
    # 智能选择MCP服务
    if "deepwiki.org" in url.lower():
        # DeepWiki MCP 专门处理 deepwiki.org 域名
        try:
            logger.info(f"🔍 检测到 deepwiki.org 链接，使用异步 DeepWiki MCP: {url}")
            result = call_deepwiki_mcp_async(url)
            
            if result.success and result.data and len(result.data.strip()) > 10:
                logger.info(f"✅ DeepWiki MCP异步调用成功，内容长度: {len(result.data)}, 耗时: {result.execution_time:.2f}s")
                return True, result.data
            else:
                logger.warning(f"⚠️ DeepWiki MCP失败，改用 Fetch MCP: {result.error_message}")
        except Exception as e:
            logger.error(f"❌ DeepWiki MCP调用异常，改用 Fetch MCP: {str(e)}")
    
    # 使用通用的异步 Fetch MCP 服务
    try:
        logger.info(f"🌐 使用异步 Fetch MCP 获取内容: {url}")
        result = call_fetch_mcp_async(url, max_length=8000)  # 增加长度限制
        
        if result.success and result.data and len(result.data.strip()) > 10:
            logger.info(f"✅ Fetch MCP异步调用成功，内容长度: {len(result.data)}, 耗时: {result.execution_time:.2f}s")
            return True, result.data
        else:
            logger.warning(f"⚠️ Fetch MCP调用失败: {result.error_message}")
            return False, f"MCP服务调用失败: {result.error_message or '未知错误'}"
    except Exception as e:
        logger.error(f"❌ Fetch MCP调用异常: {str(e)}")
        return False, f"MCP服务调用异常: {str(e)}"

def get_mcp_status_display() -> str:
    """获取MCP服务状态显示"""
    try:
        from enhanced_mcp_client import async_mcp_client

        # 快速测试两个服务的连通性
        services_status = []

        # 测试Fetch MCP
        fetch_test_result = async_mcp_client.call_mcp_service_async(
            "fetch", "fetch", {"url": "https://httpbin.org/get", "max_length": 100}
        )
        fetch_ok = fetch_test_result.success
        fetch_time = fetch_test_result.execution_time

        # 测试DeepWiki MCP
        deepwiki_test_result = async_mcp_client.call_mcp_service_async(
            "deepwiki", "deepwiki_fetch", {"url": "https://deepwiki.org/openai/openai-python", "mode": "aggregate"}
        )
        deepwiki_ok = deepwiki_test_result.success
        deepwiki_time = deepwiki_test_result.execution_time

        # 构建状态显示
        fetch_icon = "✅" if fetch_ok else "❌"
        deepwiki_icon = "✅" if deepwiki_ok else "❌"

        status_lines = [
            "## 🚀 异步MCP服务状态",
            f"- {fetch_icon} **Fetch MCP**: {'在线' if fetch_ok else '离线'} (通用网页抓取)"
        ]
        
        if fetch_ok:
            status_lines.append(f"  ⏱️ 响应时间: {fetch_time:.2f}秒")
        
        status_lines.append(f"- {deepwiki_icon} **DeepWiki MCP**: {'在线' if deepwiki_ok else '离线'} (仅限 deepwiki.org)")
        
        if deepwiki_ok:
            status_lines.append(f"  ⏱️ 响应时间: {deepwiki_time:.2f}秒")
        
        status_lines.extend([
            "",
            "🧠 **智能异步路由:**",
            "- `deepwiki.org` → DeepWiki MCP (异步处理)",
            "- 其他网站 → Fetch MCP (异步处理)", 
            "- HTTP 202 → SSE监听 → 结果获取",
            "- 自动降级 + 错误恢复"
        ])
        
        return "\n".join(status_lines)
        
    except Exception as e:
        return f"## MCP服务状态\n- ❌ **检查失败**: {str(e)}\n- 💡 请确保enhanced_mcp_client.py文件存在"

def call_mcp_service(url: str, payload: Dict[str, Any], service_name: str, timeout: int = 120) -> Tuple[bool, str]:
    """统一的MCP服务调用函数
    
    Args:
        url: MCP服务URL
        payload: 请求载荷
        service_name: 服务名称（用于日志）
        timeout: 超时时间
        
    Returns:
        (success, data): 成功标志和返回数据
    """
    try:
        logger.info(f"🔥 DEBUG: Calling {service_name} MCP service at {url}")
        logger.info(f"🔥 DEBUG: Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=timeout
        )
        
        logger.info(f"🔥 DEBUG: Response status: {response.status_code}")
        logger.info(f"🔥 DEBUG: Response headers: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            logger.info(f"🔥 DEBUG: Response JSON: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
        except:
            response_text = response.text[:1000]  # 只打印前1000个字符
            logger.info(f"🔥 DEBUG: Response text: {response_text}")
        
        if response.status_code == 200:
            data = response.json()
            
            # 检查多种可能的响应格式
            content = None
            if "data" in data and data["data"]:
                content = data["data"]
            elif "result" in data and data["result"]:
                content = data["result"]
            elif "content" in data and data["content"]:
                content = data["content"]
            elif "message" in data and data["message"]:
                content = data["message"]
            else:
                # 如果以上都没有，尝试直接使用整个响应
                content = str(data)
            
            if content and len(str(content).strip()) > 10:
                logger.info(f"✅ {service_name} MCP service returned {len(str(content))} characters")
                return True, str(content)
            else:
                logger.warning(f"⚠️ {service_name} MCP service returned empty or invalid data: {data}")
                return False, f"❌ {service_name} MCP返回空数据或格式错误"
        else:
            logger.error(f"❌ {service_name} MCP service failed with status {response.status_code}")
            logger.error(f"❌ Response content: {response.text[:500]}")
            return False, f"❌ {service_name} MCP调用失败: HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        logger.error(f"⏰ {service_name} MCP service timeout after {timeout}s")
        return False, f"❌ {service_name} MCP调用超时"
    except requests.exceptions.ConnectionError as e:
        logger.error(f"🔌 {service_name} MCP service connection failed: {str(e)}")
        return False, f"❌ {service_name} MCP连接失败"
    except Exception as e:
        logger.error(f"💥 {service_name} MCP service error: {str(e)}")
        return False, f"❌ {service_name} MCP调用错误: {str(e)}"

def fetch_external_knowledge(reference_url: str) -> str:
    """获取外部知识库内容 - 使用模块化MCP管理器，防止虚假链接生成"""
    if not reference_url or not reference_url.strip():
        return ""
    
    # 验证URL是否可访问
    url = reference_url.strip()
    logger.info(f"🔍 开始处理外部参考链接: {url}")
    
    try:
        # 简单的HEAD请求检查URL是否存在
        logger.info(f"🌐 验证链接可访问性: {url}")
        response = requests.head(url, timeout=10, allow_redirects=True)
        logger.info(f"📡 链接验证结果: HTTP {response.status_code}")
        
        if response.status_code >= 400:
            logger.warning(f"⚠️ 提供的URL不可访问: {url} (HTTP {response.status_code})")
            return f"""
## ⚠️ 参考链接状态提醒

**🔗 提供的链接**: {url}

**❌ 链接状态**: 无法访问 (HTTP {response.status_code})

**💡 建议**: 
- 请检查链接是否正确
- 或者移除参考链接，使用纯AI生成模式
- AI将基于创意描述生成专业的开发方案

---
"""
        else:
            logger.info(f"✅ 链接可访问，状态码: {response.status_code}")
            
    except requests.exceptions.Timeout:
        logger.warning(f"⏰ URL验证超时: {url}")
        return f"""
## 🔗 参考链接处理说明

**📍 提供的链接**: {url}

**⏰ 处理状态**: 链接验证超时

**🤖 AI处理**: 将基于创意内容进行智能分析，不依赖外部链接

**💡 说明**: 为确保生成质量，AI会根据创意描述生成完整方案，避免引用不确定的外部内容

---
"""
    except Exception as e:
        logger.warning(f"⚠️ URL验证失败: {url} - {str(e)}")
        return f"""
## 🔗 参考链接处理说明

**📍 提供的链接**: {url}

**🔍 处理状态**: 暂时无法验证链接可用性 ({str(e)[:100]})

**🤖 AI处理**: 将基于创意内容进行智能分析，不依赖外部链接

**💡 说明**: 为确保生成质量，AI会根据创意描述生成完整方案，避免引用不确定的外部内容

---
"""
    
    # 尝试调用MCP服务
    logger.info(f"🔄 尝试调用MCP服务获取知识...")
    mcp_start_time = datetime.now()
    success, knowledge = fetch_knowledge_from_url_via_mcp(url)
    mcp_duration = (datetime.now() - mcp_start_time).total_seconds()
    
    logger.info(f"📊 MCP服务调用结果: 成功={success}, 内容长度={len(knowledge) if knowledge else 0}, 耗时={mcp_duration:.2f}秒")
    
    if success and knowledge and len(knowledge.strip()) > 50:
        # MCP服务成功返回有效内容
        logger.info(f"✅ MCP服务成功获取知识，内容长度: {len(knowledge)} 字符")
        
        # 验证返回的内容是否包含实际知识而不是错误信息
        if not any(keyword in knowledge.lower() for keyword in ['error', 'failed', '错误', '失败', '不可用']):
            return f"""
## 📚 外部知识库参考

**🔗 来源链接**: {url}

**✅ 获取状态**: MCP服务成功获取

**📊 内容概览**: 已获取 {len(knowledge)} 字符的参考资料

---

{knowledge}

---
"""
        else:
            logger.warning(f"⚠️ MCP返回内容包含错误信息: {knowledge[:200]}")
    else:
        # MCP服务失败或返回无效内容，提供明确说明
        logger.warning(f"⚠️ MCP服务调用失败或返回无效内容")
        
        # 详细诊断MCP服务状态
        mcp_status = get_mcp_status_display()
        logger.info(f"🔍 MCP服务状态详情: {mcp_status}")
        
        return f"""
## 🔗 外部知识处理说明

**📍 参考链接**: {url}

**🎯 处理方式**: 智能分析模式

**� MCP服务状态**: 
{mcp_status}

**�💭 处理策略**: 当前外部知识服务暂时不可用，AI将基于以下方式生成方案：
- ✅ 基于创意描述进行深度分析
- ✅ 结合行业最佳实践
- ✅ 提供完整的技术方案
- ✅ 生成实用的编程提示词

**🎉 优势**: 确保生成内容的准确性和可靠性，避免引用不确定的外部信息

**🔧 技术细节**: 
- MCP调用耗时: {mcp_duration:.2f}秒
- 返回内容长度: {len(knowledge) if knowledge else 0} 字符
- 服务状态: {'成功' if success else '失败'}

---
"""

def generate_enhanced_reference_info(url: str, source_type: str, error_msg: str = None) -> str:
    """生成增强的参考信息，当MCP服务不可用时提供有用的上下文"""
    from urllib.parse import urlparse
    
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

def validate_and_fix_content(content: str) -> str:
    """验证和修复生成的内容，包括Mermaid语法、链接验证等"""
    if not content:
        return content
    
    logger.info("🔍 开始内容验证和修复...")
    
    # 记录修复项目
    fixes_applied = []
    
    # 计算初始质量分数
    initial_quality_score = calculate_quality_score(content)
    logger.info(f"📊 初始内容质量分数: {initial_quality_score}/100")
    
    # 1. 修复Mermaid图表语法错误
    original_content = content
    content = fix_mermaid_syntax(content)
    if content != original_content:
        fixes_applied.append("修复Mermaid图表语法")
    
    # 2. 验证和清理虚假链接
    original_content = content
    content = validate_and_clean_links(content)
    if content != original_content:
        fixes_applied.append("清理虚假链接")
    
    # 3. 修复日期一致性
    original_content = content
    content = fix_date_consistency(content)
    if content != original_content:
        fixes_applied.append("更新过期日期")
    
    # 4. 修复格式问题
    original_content = content
    content = fix_formatting_issues(content)
    if content != original_content:
        fixes_applied.append("修复格式问题")
    
    # 重新计算质量分数
    final_quality_score = calculate_quality_score(content)
    
    # 移除质量报告显示，只记录日志
    if final_quality_score > initial_quality_score + 5:
        improvement = final_quality_score - initial_quality_score
        logger.info(f"📈 内容质量提升: {initial_quality_score}/100 → {final_quality_score}/100 (提升{improvement}分)")
        if fixes_applied:
            logger.info(f"🔧 应用修复: {', '.join(fixes_applied)}")
    
    logger.info(f"✅ 内容验证和修复完成，最终质量分数: {final_quality_score}/100")
    if fixes_applied:
        logger.info(f"🔧 应用了以下修复: {', '.join(fixes_applied)}")
    
    return content

def calculate_quality_score(content: str) -> int:
    """计算内容质量分数（0-100）"""
    if not content:
        return 0
    
    score = 0
    max_score = 100
    
    # 1. 基础内容完整性 (30分)
    if len(content) > 500:
        score += 15
    if len(content) > 2000:
        score += 15
    
    # 2. 结构完整性 (25分)
    structure_checks = [
        '# 🚀 AI生成的开发计划',  # 标题
        '## 🤖 AI编程助手提示词',   # AI提示词部分
        '```mermaid',              # Mermaid图表
        '项目开发甘特图',           # 甘特图
    ]
    
    for check in structure_checks:
        if check in content:
            score += 6
    
    # 3. 日期准确性 (20分)
    import re
    current_year = datetime.now().year
    
    # 检查是否有当前年份或以后的日期
    recent_dates = re.findall(r'202[5-9]-\d{2}-\d{2}', content)
    if recent_dates:
        score += 10
    
    # 检查是否没有过期日期
    old_dates = re.findall(r'202[0-3]-\d{2}-\d{2}', content)
    if not old_dates:
        score += 10
    
    # 4. 链接质量 (15分)
    fake_link_patterns = [
        r'blog\.csdn\.net/username',
        r'github\.com/username', 
        r'example\.com',
        r'xxx\.com'
    ]
    
    has_fake_links = any(re.search(pattern, content, re.IGNORECASE) for pattern in fake_link_patterns)
    if not has_fake_links:
        score += 15
    
    # 5. Mermaid语法质量 (10分)
    mermaid_issues = [
        r'## 🎯 [A-Z]',  # 错误的标题在图表中
        r'```mermaid\n## 🎯',  # 格式错误
    ]
    
    has_mermaid_issues = any(re.search(pattern, content, re.MULTILINE) for pattern in mermaid_issues)
    if not has_mermaid_issues:
        score += 10
    
    return min(score, max_score)

def fix_mermaid_syntax(content: str) -> str:
    """修复Mermaid图表中的语法错误并优化渲染"""
    import re
    
    # 修复常见的Mermaid语法错误
    fixes = [
        # 移除图表代码中的额外符号和标记
        (r'## 🎯 ([A-Z]\s*-->)', r'\1'),
        (r'## 🎯 (section [^)]+)', r'\1'),
        (r'(\n|\r\n)## 🎯 ([A-Z]\s*-->)', r'\n    \2'),
        (r'(\n|\r\n)## 🎯 (section [^\n]+)', r'\n    \2'),
        
        # 修复节点定义中的多余符号
        (r'## 🎯 ([A-Z]\[[^\]]+\])', r'\1'),
        
        # 确保Mermaid代码块格式正确
        (r'```mermaid\n## 🎯', r'```mermaid'),
        
        # 移除标题级别错误
        (r'\n##+ 🎯 ([A-Z])', r'\n    \1'),
        
        # 修复中文节点名称的问题 - 彻底清理引号格式
        (r'([A-Z]+)\["([^"]+)"\]', r'\1["\2"]'),  # 标准格式：A["文本"]
        (r'([A-Z]+)\[""([^"]+)""\]', r'\1["\2"]'),  # 双引号错误：A[""文本""]
        (r'([A-Z]+)\["⚡"([^"]+)""\]', r'\1["\2"]'),  # 带emoji错误
        (r'([A-Z]+)\[([^\]]*[^\x00-\x7F][^\]]*)\]', r'\1["\2"]'),  # 中文无引号
        
        # 确保流程图语法正确
        (r'graph TB\n\s*graph', r'graph TB'),
        (r'flowchart TD\n\s*flowchart', r'flowchart TD'),
        
        # 修复箭头语法
        (r'-->', r' --> '),
        (r'-->([A-Z])', r'--> \1'),
        (r'([A-Z])-->', r'\1 -->'),
    ]
    
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # 添加Mermaid渲染增强标记
    content = enhance_mermaid_blocks(content)
    
    return content

def enhance_mermaid_blocks(content: str) -> str:
    """简化Mermaid代码块处理，避免渲染冲突"""
    import re
    
    # 查找所有Mermaid代码块并直接返回，不添加额外包装器
    # 因为包装器可能导致渲染问题
    mermaid_pattern = r'```mermaid\n(.*?)\n```'
    
    def clean_mermaid_block(match):
        mermaid_content = match.group(1)
        # 直接返回清理过的Mermaid块
        return f'```mermaid\n{mermaid_content}\n```'
    
    content = re.sub(mermaid_pattern, clean_mermaid_block, content, flags=re.DOTALL)
    
    return content

def validate_and_clean_links(content: str) -> str:
    """验证和清理虚假链接，增强链接质量"""
    import re
    
    # 检测并移除虚假链接模式
    fake_link_patterns = [
        # Markdown链接格式
        r'\[([^\]]+)\]\(https?://blog\.csdn\.net/username/article/details/\d+\)',
        r'\[([^\]]+)\]\(https?://github\.com/username/[^\)]+\)',
        r'\[([^\]]+)\]\(https?://[^/]*example\.com[^\)]*\)',
        r'\[([^\]]+)\]\(https?://[^/]*xxx\.com[^\)]*\)',
        r'\[([^\]]+)\]\(https?://[^/]*test\.com[^\)]*\)',
        r'\[([^\]]+)\]\(https?://localhost[^\)]*\)',
        
        # 新增：更多虚假链接模式
        r'\[([^\]]+)\]\(https?://medium\.com/@[^/]+/[^\)]*\d{9,}[^\)]*\)',  # Medium虚假文章
        r'\[([^\]]+)\]\(https?://github\.com/[^/]+/[^/\)]*education[^\)]*\)',  # GitHub虚假教育项目
        r'\[([^\]]+)\]\(https?://www\.kdnuggets\.com/\d{4}/\d{2}/[^\)]*\)',  # KDNuggets虚假文章
        r'\[([^\]]+)\]\(https0://[^\)]+\)',  # 错误的协议
        
        # 纯URL格式
        r'https?://blog\.csdn\.net/username/article/details/\d+',
        r'https?://github\.com/username/[^\s\)]+',
        r'https?://[^/]*example\.com[^\s\)]*',
        r'https?://[^/]*xxx\.com[^\s\)]*',
        r'https?://[^/]*test\.com[^\s\)]*',
        r'https?://localhost[^\s\)]*',
        r'https0://[^\s\)]+',  # 错误的协议
        r'https?://medium\.com/@[^/]+/[^\s]*\d{9,}[^\s]*',
        r'https?://github\.com/[^/]+/[^/\s]*education[^\s]*',
        r'https?://www\.kdnuggets\.com/\d{4}/\d{2}/[^\s]*',
    ]
    
    for pattern in fake_link_patterns:
        # 将虚假链接替换为普通文本描述
        def replace_fake_link(match):
            if match.groups():
                return f"**{match.group(1)}** (基于行业标准)"
            else:
                return "（基于行业最佳实践）"
        
        content = re.sub(pattern, replace_fake_link, content, flags=re.IGNORECASE)
    
    # 验证并增强真实链接
    content = enhance_real_links(content)
    
    return content

def enhance_real_links(content: str) -> str:
    """验证并增强真实链接的可用性"""
    import re
    
    # 查找所有markdown链接
    link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    
    def validate_link(match):
        link_text = match.group(1)
        link_url = match.group(2)
        
        # 检查是否是有效的URL格式
        if not validate_url(link_url):
            return f"**{link_text}** (参考资源)"
        
        # 检查是否是常见的技术文档网站
        trusted_domains = [
            'docs.python.org', 'nodejs.org', 'reactjs.org', 'vuejs.org',
            'angular.io', 'flask.palletsprojects.com', 'fastapi.tiangolo.com',
            'docker.com', 'kubernetes.io', 'github.com', 'gitlab.com',
            'stackoverflow.com', 'developer.mozilla.org', 'w3schools.com',
            'jwt.io', 'redis.io', 'mongodb.com', 'postgresql.org',
            'mysql.com', 'nginx.org', 'apache.org'
        ]
        
        # 如果是受信任的域名，保留链接
        for domain in trusted_domains:
            if domain in link_url.lower():
                return f"[{link_text}]({link_url})"
        
        # 对于其他链接，转换为安全的文本引用
        return f"**{link_text}** (技术参考)"
    
    content = re.sub(link_pattern, validate_link, content)
    
    return content

def fix_date_consistency(content: str) -> str:
    """修复日期一致性问题"""
    import re
    from datetime import datetime
    
    current_year = datetime.now().year
    
    # 替换2024年以前的日期为当前年份
    old_year_patterns = [
        r'202[0-3]-\d{2}-\d{2}',  # 2020-2023的日期
        r'202[0-3]年',            # 2020-2023年
    ]
    
    for pattern in old_year_patterns:
        def replace_old_date(match):
            old_date = match.group(0)
            if '-' in old_date:
                # 日期格式：YYYY-MM-DD
                parts = old_date.split('-')
                return f"{current_year}-{parts[1]}-{parts[2]}"
            else:
                # 年份格式：YYYY年
                return f"{current_year}年"
        
        content = re.sub(pattern, replace_old_date, content)
    
    return content

def fix_formatting_issues(content: str) -> str:
    """修复格式问题"""
    import re
    
    # 修复常见的格式问题
    fixes = [
        # 修复空的或格式错误的标题
        (r'#### 🚀 \*\*$', r'#### 🚀 **开发阶段**'),
        (r'#### 🚀 第阶段：\*\*', r'#### 🚀 **第1阶段**：'),
        (r'### 📋 (\d+)\. \*\*第\d+阶段', r'### 📋 \1. **第\1阶段'),
        
        # 修复表格格式问题
        (r'\n## 🎯 \| ([^|]+) \| ([^|]+) \| ([^|]+) \|', r'\n| \1 | \2 | \3 |'),
        (r'\n### 📋 (\d+)\. \*\*([^*]+)\*\*：', r'\n**\1. \2**：'),
        (r'\n### 📋 (\d+)\. \*\*([^*]+)\*\*$', r'\n**\1. \2**'),
        
        # 修复多余的空行
        (r'\n{4,}', r'\n\n\n'),
        
        # 修复不完整的段落结束
        (r'##\n\n---', r'## 总结\n\n以上是完整的开发计划和技术方案。\n\n---'),
    ]
    
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    return content

def generate_development_plan(user_idea: str, reference_url: str = "") -> Tuple[str, str, str]:
    """
    基于用户创意生成完整的产品开发计划和对应的AI编程助手提示词。
    
    Args:
        user_idea (str): 用户的产品创意描述
        reference_url (str): 可选的参考链接
        
    Returns:
        Tuple[str, str, str]: 开发计划、AI编程提示词、临时文件路径
    """
    # 开始处理链条追踪
    explanation_manager.start_processing()
    start_time = datetime.now()
    
    # 步骤1: 验证输入
    validation_start = datetime.now()
    is_valid, error_msg = validate_input(user_idea)
    validation_duration = (datetime.now() - validation_start).total_seconds()
    
    explanation_manager.add_processing_step(
        stage=ProcessingStage.INPUT_VALIDATION,
        title="输入验证",
        description="验证用户输入的创意描述是否符合要求",
        success=is_valid,
        details={
            "输入长度": len(user_idea.strip()) if user_idea else 0,
            "包含参考链接": bool(reference_url),
            "验证结果": "通过" if is_valid else error_msg
        },
        duration=validation_duration,
        quality_score=100 if is_valid else 0,
        evidence=f"用户输入: '{user_idea[:50]}...' (长度: {len(user_idea.strip()) if user_idea else 0}字符)"
    )
    
    if not is_valid:
        return error_msg, "", None
    
    # 步骤2: API密钥检查
    api_check_start = datetime.now()
    if not API_KEY:
        api_check_duration = (datetime.now() - api_check_start).total_seconds()
        explanation_manager.add_processing_step(
            stage=ProcessingStage.AI_GENERATION,
            title="API密钥检查",
            description="检查AI模型API密钥配置",
            success=False,
            details={"错误": "API密钥未配置"},
            duration=api_check_duration,
            quality_score=0,
            evidence="系统环境变量中未找到SILICONFLOW_API_KEY"
        )
        
        logger.error("API key not configured")
        error_msg = """
## ❌ 配置错误：未设置API密钥

### 🔧 解决方法：

1. **获取API密钥**：
   - 访问 [Silicon Flow](https://siliconflow.cn) 
   - 注册账户并获取API密钥

2. **配置环境变量**：
   ```bash
   export SILICONFLOW_API_KEY=your_api_key_here
   ```

3. **魔塔平台配置**：
   - 在创空间设置中添加环境变量
   - 变量名：`SILICONFLOW_API_KEY`
   - 变量值：你的实际API密钥

### 📋 配置完成后重启应用即可使用完整功能！

---

**💡 提示**：API密钥是必填项，没有它就无法调用AI服务生成开发计划。
"""
        return error_msg, "", None
    
    # 步骤3: 获取外部知识库内容
    knowledge_start = datetime.now()
    retrieved_knowledge = fetch_external_knowledge(reference_url)
    knowledge_duration = (datetime.now() - knowledge_start).total_seconds()
    
    explanation_manager.add_processing_step(
        stage=ProcessingStage.KNOWLEDGE_RETRIEVAL,
        title="外部知识获取",
        description="从MCP服务获取外部参考知识",
        success=bool(retrieved_knowledge and "成功获取" in retrieved_knowledge),
        details={
            "参考链接": reference_url or "无",
            "MCP服务状态": get_mcp_status_display(),
            "知识内容长度": len(retrieved_knowledge) if retrieved_knowledge else 0
        },
        duration=knowledge_duration,
        quality_score=80 if retrieved_knowledge else 50,
        evidence=f"获取的知识内容: '{retrieved_knowledge[:100]}...' (长度: {len(retrieved_knowledge) if retrieved_knowledge else 0}字符)"
    )
    
    # 获取当前日期并计算项目开始日期
    current_date = datetime.now()
    # 项目开始日期：下周一开始（给用户准备时间）
    days_until_monday = (7 - current_date.weekday()) % 7
    if days_until_monday == 0:  # 如果今天是周一，则下周一开始
        days_until_monday = 7
    project_start_date = current_date + timedelta(days=days_until_monday)
    project_start_str = project_start_date.strftime("%Y-%m-%d")
    current_year = current_date.year
    
    # 构建系统提示词 - 防止虚假链接生成，强化编程提示词生成，增强视觉化内容，加强日期上下文
    system_prompt = f"""你是一个资深技术项目经理，精通产品规划和 AI 编程助手（如 GitHub Copilot、ChatGPT Code）提示词撰写。

📅 **当前时间上下文**：今天是 {current_date.strftime("%Y年%m月%d日")}，当前年份是 {current_year} 年。所有项目时间必须基于当前时间合理规划。

🔴 重要要求：
1. 当收到外部知识库参考时，你必须在开发计划中明确引用和融合这些信息
2. 必须在开发计划的开头部分提及参考来源（如CSDN博客、GitHub项目等）
3. 必须根据外部参考调整技术选型和实施建议
4. 必须在相关章节中使用"参考XXX建议"等表述
5. 开发阶段必须有明确编号（第1阶段、第2阶段等）

🚫 严禁行为（严格执行）：
- **绝对不要编造任何虚假的链接或参考资料**
- **禁止生成任何不存在的URL，包括但不限于：**
  - ❌ https://medium.com/@username/... (用户名+数字ID格式)
  - ❌ https://github.com/username/... (占位符用户名)
  - ❌ https://blog.csdn.net/username/... 
  - ❌ https://www.kdnuggets.com/年份/月份/... (虚构文章)
  - ❌ https://example.com, xxx.com, test.com 等测试域名
  - ❌ 任何以https0://开头的错误协议链接
- **不要在"参考来源"部分添加任何链接，除非用户明确提供**
- **不要使用"参考文献"、"延伸阅读"等标题添加虚假链接**

✅ 正确做法：
- 如果没有提供外部参考，**完全省略"参考来源"部分**
- 只引用用户实际提供的参考链接（如果有的话）
- 当外部知识不可用时，明确说明是基于最佳实践生成
- 使用 "基于行业标准"、"参考常见架构"、"遵循最佳实践" 等表述
- **开发计划应直接开始，不要虚构任何外部资源**

📊 视觉化内容要求（新增）：
- 必须在技术方案中包含架构图的Mermaid代码
- 必须在开发计划中包含甘特图的Mermaid代码
- 必须在功能模块中包含流程图的Mermaid代码
- 必须包含技术栈对比表格
- 必须包含项目里程碑时间表

🎯 Mermaid图表格式要求（严格遵循）：

⚠️ **严格禁止错误格式**：
- ❌ 绝对不要使用 `A[""文本""]` 格式（双重引号）
- ❌ 绝对不要使用 `## 🎯` 等标题在图表内部
- ❌ 绝对不要在节点名称中使用emoji符号

✅ **正确的Mermaid语法**：

**架构图示例**：
```mermaid
flowchart TD
    A["用户界面"] --> B["业务逻辑层"]
    B --> C["数据访问层"]
    C --> D["数据库"]
    B --> E["外部API"]
    F["缓存"] --> B
```

**流程图示例**：
```mermaid
flowchart TD
    Start([开始]) --> Input[用户输入]
    Input --> Validate{{验证输入}}
    Validate -->|有效| Process[处理数据]
    Validate -->|无效| Error[显示错误]
    Process --> Save[保存结果]
    Save --> Success[成功提示]
    Error --> Input
    Success --> End([结束])
```

**甘特图示例（必须使用真实的项目开始日期）**：
```mermaid
gantt
    title 项目开发甘特图
    dateFormat YYYY-MM-DD
    axisFormat %m-%d
    
    section 需求分析
    需求调研     :done, req1, {project_start_str}, 3d
    需求整理     :done, req2, after req1, 4d
    
    section 系统设计
    架构设计     :active, design1, after req2, 7d
    UI设计       :design2, after design1, 5d
    
    section 开发实施
    后端开发     :dev1, after design2, 14d
    前端开发     :dev2, after design2, 14d
    集成测试     :test1, after dev1, 7d
    
    section 部署上线
    部署准备     :deploy1, after test1, 3d
    正式上线     :deploy2, after deploy1, 2d
```

⚠️ **日期生成规则**：
- 项目开始日期：{project_start_str}（下周一开始）
- 所有日期必须基于 {current_year} 年及以后
- 严禁使用 2024 年以前的日期
- 里程碑日期必须与甘特图保持一致

🎯 必须严格按照Mermaid语法规范生成图表，不能有格式错误

🎯 AI编程提示词格式要求（重要）：
- 必须在开发计划后生成专门的"# AI编程助手提示词"部分
- 每个功能模块必须有一个专门的AI编程提示词
- 每个提示词必须使用```代码块格式，方便复制
- 提示词内容要基于具体项目功能，不要使用通用模板
- 提示词要详细、具体、可直接用于AI编程工具
- 必须包含完整的上下文和具体要求

🔧 提示词结构要求：
每个提示词使用以下格式：

## [功能名称]开发提示词

```
请为[具体项目名称]开发[具体功能描述]。

项目背景：
[基于开发计划的项目背景]

功能要求：
1. [具体要求1]
2. [具体要求2]
...

技术约束：
- 使用[具体技术栈]
- 遵循[具体规范]
- 实现[具体性能要求]

输出要求：
- 完整可运行代码
- 详细注释说明
- 错误处理机制
- 测试用例
```

请严格按照此格式生成个性化的编程提示词，确保每个提示词都基于具体项目需求。

格式要求：先输出开发计划，然后输出编程提示词部分。"""

    # 构建用户提示词
    user_prompt = f"""产品创意：{user_idea}"""
    
    # 如果成功获取到外部知识，则注入到提示词中
    if retrieved_knowledge and not any(keyword in retrieved_knowledge for keyword in ["❌", "⚠️", "处理说明", "暂时不可用"]):
        user_prompt += f"""

# 外部知识库参考
{retrieved_knowledge}

请基于上述外部知识库参考和产品创意生成："""
    else:
        user_prompt += """

请生成："""
    
    user_prompt += """
1. 详细的开发计划（包含产品概述、技术方案、开发计划、部署方案、推广策略等）
2. 每个功能模块对应的AI编程助手提示词

确保提示词具体、可操作，能直接用于AI编程工具。"""

    try:
        logger.info("🚀 开始调用AI API生成开发计划...")
        
        # 步骤3: AI生成准备
        ai_prep_start = datetime.now()
        
        # 构建请求数据
        request_data = {
            "model": "Qwen/Qwen2.5-72B-Instruct",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 4096,  # 修复：API限制最大4096 tokens
            "temperature": 0.7
        }
        
        ai_prep_duration = (datetime.now() - ai_prep_start).total_seconds()
        
        explanation_manager.add_processing_step(
            stage=ProcessingStage.AI_GENERATION,
            title="AI请求准备",
            description="构建AI模型请求参数和提示词",
            success=True,
            details={
                "AI模型": request_data['model'],
                "系统提示词长度": f"{len(system_prompt)} 字符",
                "用户提示词长度": f"{len(user_prompt)} 字符",
                "最大Token数": request_data['max_tokens'],
                "温度参数": request_data['temperature']
            },
            duration=ai_prep_duration,
            quality_score=95,
            evidence=f"准备调用 {request_data['model']} 模型，提示词总长度: {len(system_prompt + user_prompt)} 字符"
        )
        
        # 记录请求信息（不包含完整提示词以避免日志过长）
        logger.info(f"📊 API请求模型: {request_data['model']}")
        logger.info(f"📏 系统提示词长度: {len(system_prompt)} 字符")
        logger.info(f"📏 用户提示词长度: {len(user_prompt)} 字符")
        
        # 步骤4: AI API调用
        api_call_start = datetime.now()
        logger.info(f"🌐 正在调用API: {API_URL}")
        
        response = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json=request_data,
            timeout=300  # 优化：生成方案超时时间为300秒（5分钟）
        )
        
        api_call_duration = (datetime.now() - api_call_start).total_seconds()
        
        logger.info(f"📈 API响应状态码: {response.status_code}")
        logger.info(f"⏱️ API调用耗时: {api_call_duration:.2f}秒")
        
        if response.status_code == 200:
            content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            
            content_length = len(content) if content else 0
            logger.info(f"📝 生成内容长度: {content_length} 字符")
            
            explanation_manager.add_processing_step(
                stage=ProcessingStage.AI_GENERATION,
                title="AI内容生成",
                description="AI模型成功生成开发计划内容",
                success=bool(content),
                details={
                    "响应状态": f"HTTP {response.status_code}",
                    "生成内容长度": f"{content_length} 字符",
                    "API调用耗时": f"{api_call_duration:.2f}秒",
                    "平均生成速度": f"{content_length / api_call_duration:.1f} 字符/秒" if api_call_duration > 0 else "N/A"
                },
                duration=api_call_duration,
                quality_score=90 if content_length > 1000 else 70,
                evidence=f"成功生成 {content_length} 字符的开发计划内容，包含技术方案和编程提示词"
            )
            
            if content:
                # 步骤5: 内容后处理
                postprocess_start = datetime.now()
                
                # 后处理：确保内容结构化
                final_plan_text = format_response(content)
                
                # 应用内容验证和修复
                final_plan_text = validate_and_fix_content(final_plan_text)
                
                postprocess_duration = (datetime.now() - postprocess_start).total_seconds()
                
                explanation_manager.add_processing_step(
                    stage=ProcessingStage.CONTENT_FORMATTING,
                    title="内容后处理",
                    description="格式化和验证生成的内容",
                    success=True,
                    details={
                        "格式化处理": "Markdown结构优化",
                        "内容验证": "Mermaid语法修复, 链接检查",
                        "最终内容长度": f"{len(final_plan_text)} 字符",
                        "处理耗时": f"{postprocess_duration:.2f}秒"
                    },
                    duration=postprocess_duration,
                    quality_score=85,
                    evidence=f"完成内容后处理，最终输出 {len(final_plan_text)} 字符的完整开发计划"
                )
                
                # 创建临时文件
                temp_file = create_temp_markdown_file(final_plan_text)
                
                # 如果临时文件创建失败，使用None避免Gradio权限错误
                if not temp_file:
                    temp_file = None
                
                # 总处理时间
                total_duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"🎉 开发计划生成完成，总耗时: {total_duration:.2f}秒")
                
                return final_plan_text, extract_prompts_section(final_plan_text), temp_file
            else:
                explanation_manager.add_processing_step(
                    stage=ProcessingStage.AI_GENERATION,
                    title="AI生成失败",
                    description="AI模型返回空内容",
                    success=False,
                    details={
                        "响应状态": f"HTTP {response.status_code}",
                        "错误原因": "AI返回空内容"
                    },
                    duration=api_call_duration,
                    quality_score=0,
                    evidence="AI API调用成功但返回空的内容"
                )
                
                logger.error("API returned empty content")
                return "❌ AI返回空内容，请稍后重试", "", None
        else:
            # 记录详细的错误信息
            logger.error(f"API request failed with status {response.status_code}")
            try:
                error_detail = response.json()
                logger.error(f"API错误详情: {error_detail}")
                error_message = error_detail.get('message', '未知错误')
                error_code = error_detail.get('code', '')
                
                explanation_manager.add_processing_step(
                    stage=ProcessingStage.AI_GENERATION,
                    title="AI API调用失败",
                    description="AI模型API请求失败",
                    success=False,
                    details={
                        "HTTP状态码": response.status_code,
                        "错误代码": error_code,
                        "错误消息": error_message
                    },
                    duration=api_call_duration,
                    quality_score=0,
                    evidence=f"API返回错误: HTTP {response.status_code} - {error_message}"
                )
                
                return f"❌ API请求失败: HTTP {response.status_code} (错误代码: {error_code}) - {error_message}", "", None
            except:
                logger.error(f"API响应内容: {response.text[:500]}")
                
                explanation_manager.add_processing_step(
                    stage=ProcessingStage.AI_GENERATION,
                    title="AI API调用失败",
                    description="AI模型API请求失败，无法解析错误信息",
                    success=False,
                    details={
                        "HTTP状态码": response.status_code,
                        "响应内容": response.text[:200]
                    },
                    duration=api_call_duration,
                    quality_score=0,
                    evidence=f"API请求失败，状态码: {response.status_code}"
                )
                
                return f"❌ API请求失败: HTTP {response.status_code} - {response.text[:200]}", "", None
            
    except requests.exceptions.Timeout:
        logger.error("API request timeout")
        return "❌ API请求超时，请稍后重试", "", None
    except requests.exceptions.ConnectionError:
        logger.error("API connection failed")
        return "❌ 网络连接失败，请检查网络设置", "", None
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return f"❌ 处理错误: {str(e)}", "", None

def extract_prompts_section(content: str) -> str:
    """从完整内容中提取AI编程提示词部分"""
    lines = content.split('\n')
    prompts_section = []
    in_prompts_section = False
    
    for line in lines:
        if any(keyword in line for keyword in ['编程提示词', '编程助手', 'Prompt', 'AI助手']):
            in_prompts_section = True
        if in_prompts_section:
            prompts_section.append(line)
    
    return '\n'.join(prompts_section) if prompts_section else "未找到编程提示词部分"

def create_temp_markdown_file(content: str) -> str:
    """创建临时markdown文件"""
    try:
        import tempfile
        import os
        
        # 创建临时文件，使用更安全的方法
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.md', 
            delete=False, 
            encoding='utf-8'
        ) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # 验证文件是否创建成功
        if os.path.exists(temp_file_path):
            logger.info(f"✅ 成功创建临时文件: {temp_file_path}")
            return temp_file_path
        else:
            logger.warning("⚠️ 临时文件创建后不存在")
            return ""
            
    except PermissionError as e:
        logger.error(f"❌ 权限错误，无法创建临时文件: {e}")
        return ""
    except Exception as e:
        logger.error(f"❌ 创建临时文件失败: {e}")
        return ""

def enable_plan_editing(plan_content: str) -> Tuple[str, str]:
    """启用方案编辑功能"""
    try:
        # 解析方案内容
        sections = plan_editor.parse_plan_content(plan_content)
        editable_sections = plan_editor.get_editable_sections()
        
        # 生成编辑界面HTML
        edit_interface = generate_edit_interface(editable_sections)
        
        # 生成编辑摘要
        summary = plan_editor.get_edit_summary()
        edit_summary = f"""
## 📝 方案编辑模式已启用

**📊 编辑统计**：
- 总段落数：{summary['total_sections']}
- 可编辑段落：{summary['editable_sections']}
- 已编辑段落：{summary['edited_sections']}

**💡 编辑说明**：
- 点击下方段落可进行编辑
- 系统会自动保存编辑历史
- 可随时恢复到原始版本

---
"""
        
        return edit_interface, edit_summary
        
    except Exception as e:
        logger.error(f"启用编辑失败: {str(e)}")
        return "", f"❌ 启用编辑失败: {str(e)}"

def generate_edit_interface(editable_sections: List[Dict]) -> str:
    """生成编辑界面HTML"""
    interface_html = """
<div class="plan-editor-container">
    <div class="editor-header">
        <h3>📝 分段编辑器</h3>
        <p>点击任意段落进行编辑，系统会自动保存您的更改</p>
    </div>
    
    <div class="sections-container">
"""
    
    for section in editable_sections:
        section_html = f"""
        <div class="editable-section" data-section-id="{section['id']}" data-section-type="{section['type']}">
            <div class="section-header">
                <span class="section-type">{get_section_type_emoji(section['type'])}</span>
                <span class="section-title">{section['title']}</span>
                <button class="edit-section-btn" onclick="editSection('{section['id']}')">
                    ✏️ 编辑
                </button>
            </div>
            
            <div class="section-preview">
                <div class="preview-content">{section['preview']}</div>
                <div class="section-content" style="display: none;">{_html_escape(section['content'])}</div>
            </div>
        </div>
"""
        interface_html += section_html
    
    interface_html += """
    </div>
    
    <div class="editor-actions">
        <button class="apply-changes-btn" onclick="applyAllChanges()">
            ✅ 应用所有更改
        </button>
        <button class="reset-changes-btn" onclick="resetAllChanges()">
            🔄 重置所有更改
        </button>
    </div>
</div>

<script>
function editSection(sectionId) {
    const section = document.querySelector(`[data-section-id="${sectionId}"]`);
    const content = section.querySelector('.section-content').textContent;
    const type = section.getAttribute('data-section-type');
    
    // 检测当前主题
    const isDark = document.documentElement.classList.contains('dark');
    
    // 创建编辑对话框
    const editDialog = document.createElement('div');
    editDialog.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.6);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 10000;
    `;
    
    editDialog.innerHTML = `
        <div style="
            background: ${isDark ? '#2d3748' : 'white'};
            color: ${isDark ? '#f7fafc' : '#2d3748'};
            padding: 2rem;
            border-radius: 1rem;
            max-width: 90%;
            max-height: 90%;
            overflow-y: auto;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        ">
            <h3 style="margin-bottom: 1rem; color: ${isDark ? '#f7fafc' : '#2d3748'};">
                ✏️ 编辑段落 - ${type}
            </h3>
            <textarea
                id="section-editor-${sectionId}"
                style="
                    width: 100%;
                    height: 400px;
                    padding: 1rem;
                    border: 2px solid ${isDark ? '#4a5568' : '#e2e8f0'};
                    border-radius: 0.5rem;
                    font-family: 'Fira Code', monospace;
                    font-size: 0.9rem;
                    resize: vertical;
                    line-height: 1.6;
                    background: ${isDark ? '#1a202c' : 'white'};
                    color: ${isDark ? '#f7fafc' : '#2d3748'};
                "
                placeholder="在此编辑段落内容..."
            >${content}</textarea>
            <div style="margin-top: 1rem;">
                <label style="display: block; margin-bottom: 0.5rem;">编辑说明 (可选):</label>
                <input
                    type="text"
                    id="edit-comment-${sectionId}"
                    style="
                        width: 100%;
                        padding: 0.5rem;
                        border: 1px solid ${isDark ? '#4a5568' : '#e2e8f0'};
                        border-radius: 0.25rem;
                        background: ${isDark ? '#1a202c' : 'white'};
                        color: ${isDark ? '#f7fafc' : '#2d3748'};
                    "
                    placeholder="简要说明您的更改..."
                />
            </div>
            <div style="margin-top: 1.5rem; display: flex; gap: 1rem; justify-content: flex-end;">
                <button
                    onclick="document.body.removeChild(this.closest('.edit-dialog-overlay'))"
                    style="
                        padding: 0.5rem 1rem;
                        border: 1px solid ${isDark ? '#4a5568' : '#cbd5e0'};
                        background: ${isDark ? '#2d3748' : 'white'};
                        color: ${isDark ? '#f7fafc' : '#4a5568'};
                        border-radius: 0.5rem;
                        cursor: pointer;
                    "
                >取消</button>
                <button
                    onclick="saveSectionEdit('${sectionId}')"
                    style="
                        padding: 0.5rem 1rem;
                        background: linear-gradient(45deg, #667eea, #764ba2);
                        color: white;
                        border: none;
                        border-radius: 0.5rem;
                        cursor: pointer;
                    "
                >保存</button>
            </div>
        </div>
    `;
    
    editDialog.className = 'edit-dialog-overlay';
    document.body.appendChild(editDialog);
    
    // ESC键关闭
    const escapeHandler = (e) => {
        if (e.key === 'Escape') {
            document.body.removeChild(editDialog);
            document.removeEventListener('keydown', escapeHandler);
        }
    };
    document.addEventListener('keydown', escapeHandler);
    
    // 点击外部关闭
    editDialog.addEventListener('click', (e) => {
        if (e.target === editDialog) {
            document.body.removeChild(editDialog);
            document.removeEventListener('keydown', escapeHandler);
        }
    });
}

function saveSectionEdit(sectionId) {
    const newContent = document.getElementById(`section-editor-${sectionId}`).value;
    const comment = document.getElementById(`edit-comment-${sectionId}`).value;
    
    // 更新隐藏组件的值来触发Gradio事件
    const sectionIdInput = document.querySelector('#section_id_input textarea');
    const sectionContentInput = document.querySelector('#section_content_input textarea'); 
    const sectionCommentInput = document.querySelector('#section_comment_input textarea');
    const updateTrigger = document.querySelector('#section_update_trigger textarea');
    
    if (sectionIdInput && sectionContentInput && sectionCommentInput && updateTrigger) {
        sectionIdInput.value = sectionId;
        sectionContentInput.value = newContent;
        sectionCommentInput.value = comment;
        updateTrigger.value = Date.now().toString(); // 触发更新
        
        // 手动触发change事件
        sectionIdInput.dispatchEvent(new Event('input'));
        sectionContentInput.dispatchEvent(new Event('input'));
        sectionCommentInput.dispatchEvent(new Event('input'));
        updateTrigger.dispatchEvent(new Event('input'));
    }
    
    // 关闭对话框
    document.body.removeChild(document.querySelector('.edit-dialog-overlay'));
    
    // 更新预览
    const section = document.querySelector(`[data-section-id="${sectionId}"]`);
    const preview = section.querySelector('.preview-content');
    preview.textContent = newContent.substring(0, 100) + '...';
    
    // 显示保存成功提示
    showNotification('✅ 段落已保存', 'success');
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: ${type === 'success' ? '#48bb78' : '#4299e1'};
        color: white;
        border-radius: 0.5rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        z-index: 10001;
        animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in forwards';
        setTimeout(() => document.body.removeChild(notification), 300);
    }, 3000);
}

// 添加必要的CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);
</script>
"""
    
    return interface_html

def _html_escape(text: str) -> str:
    """HTML转义函数"""
    import html
    return html.escape(text)

def get_section_type_emoji(section_type: str) -> str:
    """获取段落类型对应的emoji"""
    type_emojis = {
        'heading': '📋',
        'paragraph': '📝',
        'list': '📄',
        'code': '💻',
        'table': '📊'
    }
    return type_emojis.get(section_type, '📝')

def update_section_content(section_id: str, new_content: str, comment: str) -> str:
    """更新段落内容"""
    try:
        success = plan_editor.update_section(section_id, new_content, comment)
        
        if success:
            # 获取更新后的完整内容
            updated_content = plan_editor.get_modified_content()
            
            # 格式化并返回
            formatted_content = format_response(updated_content)
            
            logger.info(f"段落 {section_id} 更新成功")
            return formatted_content
        else:
            logger.error(f"段落 {section_id} 更新失败")
            return "❌ 更新失败"
            
    except Exception as e:
        logger.error(f"更新段落内容失败: {str(e)}")
        return f"❌ 更新失败: {str(e)}"

def get_edit_history() -> str:
    """获取编辑历史"""
    try:
        history = plan_editor.get_edit_history()
        
        if not history:
            return "暂无编辑历史"
        
        history_html = """
<div class="edit-history">
    <h3>📜 编辑历史</h3>
    <div class="history-list">
"""
        
        for i, edit in enumerate(reversed(history[-10:]), 1):  # 显示最近10次编辑
            timestamp = datetime.fromisoformat(edit['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            history_html += f"""
            <div class="history-item">
                <div class="history-header">
                    <span class="history-index">#{i}</span>
                    <span class="history-time">{timestamp}</span>
                    <span class="history-section">段落: {edit['section_id']}</span>
                </div>
                <div class="history-comment">{edit['user_comment'] or '无说明'}</div>
            </div>
"""
        
        history_html += """
    </div>
</div>
"""
        
        return history_html
        
    except Exception as e:
        logger.error(f"获取编辑历史失败: {str(e)}")
        return f"❌ 获取编辑历史失败: {str(e)}"

def reset_plan_edits() -> str:
    """重置所有编辑"""
    try:
        plan_editor.reset_to_original()
        logger.info("已重置所有编辑")
        return "✅ 已重置到原始版本"
    except Exception as e:
        logger.error(f"重置失败: {str(e)}")
        return f"❌ 重置失败: {str(e)}"

def fix_links_for_new_window(content: str) -> str:
    """修复所有链接为新窗口打开，解决魔塔平台链接问题"""
    import re
    
    # 匹配所有markdown链接格式 [text](url)
    def replace_markdown_link(match):
        text = match.group(1)
        url = match.group(2)
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{text}</a>'
    
    # 替换markdown链接
    content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_markdown_link, content)
    
    # 匹配所有HTML链接并添加target="_blank"
    def add_target_blank(match):
        full_tag = match.group(0)
        if 'target=' not in full_tag:
            # 在>前添加target="_blank"
            return full_tag.replace('>', ' target="_blank" rel="noopener noreferrer">')
        return full_tag
    
    # 替换HTML链接
    content = re.sub(r'<a [^>]*href=[^>]*>', add_target_blank, content)
    
    return content

def format_response(content: str) -> str:
    """格式化AI回复，美化显示并保持原始AI生成的提示词"""
    
    # 修复所有链接为新窗口打开
    content = fix_links_for_new_window(content)
    
    # 添加时间戳和格式化标题
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 分割开发计划和AI编程提示词
    parts = content.split('# AI编程助手提示词')
    
    if len(parts) >= 2:
        # 有明确的AI编程提示词部分
        plan_content = parts[0].strip()
        prompts_content = '# AI编程助手提示词' + parts[1]
        
        # 美化AI编程提示词部分
        enhanced_prompts = enhance_prompts_display(prompts_content)
        
        formatted_content = f"""
<div class="plan-header">

# 🚀 AI生成的开发计划

<div class="meta-info">

**⏰ 生成时间：** {timestamp}  
**🤖 AI模型：** Qwen2.5-72B-Instruct  
**💡 基于用户创意智能分析生成**  
**🔗 Agent应用MCP服务增强**

</div>

</div>

---

{enhance_markdown_structure(plan_content)}

---

{enhanced_prompts}
"""
    else:
        # 没有明确分割，使用原始内容
        formatted_content = f"""
<div class="plan-header">

# 🚀 AI生成的开发计划

<div class="meta-info">

**⏰ 生成时间：** {timestamp}  
**🤖 AI模型：** Qwen2.5-72B-Instruct  
**💡 基于用户创意智能分析生成**  
**🔗 Agent应用MCP服务增强**

</div>

</div>

---

{enhance_markdown_structure(content)}
"""
    
    return formatted_content

def enhance_prompts_display(prompts_content: str) -> str:
    """简化AI编程提示词显示"""
    lines = prompts_content.split('\n')
    enhanced_lines = []
    in_code_block = False
    
    for line in lines:
        stripped = line.strip()
        
        # 处理标题
        if stripped.startswith('# AI编程助手提示词'):
            enhanced_lines.append('')
            enhanced_lines.append('<div class="prompts-highlight">')
            enhanced_lines.append('')
            enhanced_lines.append('# 🤖 AI编程助手提示词')
            enhanced_lines.append('')
            enhanced_lines.append('> 💡 **使用说明**：以下提示词基于您的项目需求定制生成，可直接复制到 GitHub Copilot、ChatGPT、Claude 等AI编程工具中使用')
            enhanced_lines.append('')
            continue
            
        # 处理二级标题（功能模块）
        if stripped.startswith('## ') and not in_code_block:
            title = stripped[3:].strip()
            enhanced_lines.append('')
            enhanced_lines.append(f'### 🎯 {title}')
            enhanced_lines.append('')
            continue
            
        # 处理代码块开始
        if stripped.startswith('```') and not in_code_block:
            in_code_block = True
            enhanced_lines.append('')
            enhanced_lines.append('```')
            continue
            
        # 处理代码块结束
        if stripped.startswith('```') and in_code_block:
            in_code_block = False
            enhanced_lines.append('```')
            enhanced_lines.append('')
            continue
            
        # 其他内容直接添加
        enhanced_lines.append(line)
    
    # 结束高亮区域
    enhanced_lines.append('')
    enhanced_lines.append('</div>')
    
    return '\n'.join(enhanced_lines)

def extract_prompts_section(content: str) -> str:
    """从完整内容中提取AI编程提示词部分"""
    # 分割内容，查找AI编程提示词部分
    parts = content.split('# AI编程助手提示词')
    
    if len(parts) >= 2:
        prompts_content = '# AI编程助手提示词' + parts[1]
        # 清理和格式化提示词内容，移除HTML标签以便复制
        clean_prompts = clean_prompts_for_copy(prompts_content)
        return clean_prompts
    else:
        # 如果没有找到明确的提示词部分，尝试其他关键词
        lines = content.split('\n')
        prompts_section = []
        in_prompts_section = False
        
        for line in lines:
            if any(keyword in line for keyword in ['编程提示词', '编程助手', 'Prompt', 'AI助手']):
                in_prompts_section = True
            if in_prompts_section:
                prompts_section.append(line)
        
        return '\n'.join(prompts_section) if prompts_section else "未找到编程提示词部分"

def clean_prompts_for_copy(prompts_content: str) -> str:
    """清理提示词内容，移除HTML标签，优化复制体验"""
    import re
    
    # 移除HTML标签
    clean_content = re.sub(r'<[^>]+>', '', prompts_content)
    
    # 清理多余的空行
    lines = clean_content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped:
            cleaned_lines.append(line)
        elif cleaned_lines and cleaned_lines[-1].strip():  # 避免连续空行
            cleaned_lines.append('')
    
    return '\n'.join(cleaned_lines)

# 删除多余的旧代码，这里应该是enhance_markdown_structure函数
def enhance_markdown_structure(content: str) -> str:
    """增强Markdown结构，添加视觉亮点和层级"""
    lines = content.split('\n')
    enhanced_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # 增强一级标题
        if stripped and not stripped.startswith('#') and len(stripped) < 50 and '：' not in stripped and '.' not in stripped[:5]:
            if any(keyword in stripped for keyword in ['产品概述', '技术方案', '开发计划', '部署方案', '推广策略', 'AI', '编程助手', '提示词']):
                enhanced_lines.append(f"\n## 🎯 {stripped}\n")
                continue
        
        # 增强二级标题
        if stripped and '.' in stripped[:5] and len(stripped) < 100:
            if stripped[0].isdigit():
                enhanced_lines.append(f"\n### 📋 {stripped}\n")
                continue
                
        # 增强功能列表
        if stripped.startswith('主要功能') or stripped.startswith('目标用户'):
            enhanced_lines.append(f"\n#### 🔹 {stripped}\n")
            continue
            
        # 增强技术栈部分
        if stripped in ['前端', '后端', 'AI 模型', '工具和库']:
            enhanced_lines.append(f"\n#### 🛠️ {stripped}\n")
            continue
            
        # 增强阶段标题
        if '阶段' in stripped and '：' in stripped:
            if '第' in stripped and '阶段' in stripped:
                try:
                    # 更健壮的阶段号提取逻辑
                    parts = stripped.split('第')
                    if len(parts) > 1:
                        phase_part = parts[1].split('阶段')[0].strip()
                        phase_name = stripped.split('：')[1].strip() if '：' in stripped else ''
                        enhanced_lines.append(f"\n#### 🚀 第{phase_part}阶段：{phase_name}\n")
                    else:
                        enhanced_lines.append(f"\n#### 🚀 {stripped}\n")
                except:
                    enhanced_lines.append(f"\n#### 🚀 {stripped}\n")
            else:
                enhanced_lines.append(f"\n#### 🚀 {stripped}\n")
            continue
            
        # 增强任务列表
        if stripped.startswith('任务：'):
            enhanced_lines.append(f"\n**📝 {stripped}**\n")
            continue
            
        # 保持原有缩进的其他内容
        enhanced_lines.append(line)
    
    return '\n'.join(enhanced_lines)

# 自定义CSS - 保持美化UI
custom_css = """
.main-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.header-gradient {
    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 50%, #60a5fa 100%);
    color: white;
    padding: 2.5rem;
    border-radius: 1.5rem;
    text-align: center;
    margin-bottom: 2rem;
    box-shadow: 0 10px 30px rgba(59, 130, 246, 0.3);
    position: relative;
    overflow: hidden;
}

.header-gradient::before {
    content: "";
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: linear-gradient(45deg, transparent 40%, rgba(255,255,255,0.1) 50%, transparent 60%);
    animation: shine 3s infinite;
}

@keyframes shine {
    0% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
    100% { transform: translateX(100%) translateY(100%) rotate(45deg); }
}

.content-card {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    padding: 2rem;
    border-radius: 1.5rem;
    box-shadow: 0 8px 25px rgba(59, 130, 246, 0.1);
    margin: 1rem 0;
    border: 1px solid #e2e8f0;
}

.dark .content-card {
    background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
    border-color: #374151;
}

.result-container {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    border-radius: 1.5rem;
    padding: 2rem;
    margin: 2rem 0;
    border: 2px solid #3b82f6;
    box-shadow: 0 10px 30px rgba(59, 130, 246, 0.15);
}

.dark .result-container {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-color: #60a5fa;
}

.generate-btn {
    background: linear-gradient(45deg, #3b82f6, #1d4ed8) !important;
    border: none !important;
    color: white !important;
    padding: 1rem 2.5rem !important;
    border-radius: 2rem !important;
    font-weight: 700 !important;
    font-size: 1.1rem !important;
    transition: all 0.4s ease !important;
    box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4) !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    position: relative;
    overflow: hidden;
}

.generate-btn:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 12px 35px rgba(59, 130, 246, 0.5) !important;
    background: linear-gradient(45deg, #1d4ed8, #1e40af) !important;
}

.generate-btn::before {
    content: "";
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    transition: left 0.5s;
}

.generate-btn:hover::before {
    left: 100%;
}

.tips-box {
    background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
    padding: 1.5rem;
    border-radius: 1.2rem;
    margin: 1.5rem 0;
    border: 2px solid #93c5fd;
    box-shadow: 0 6px 20px rgba(147, 197, 253, 0.2);
}

.dark .tips-box {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-color: #60a5fa;
}

.tips-box h4 {
    color: #1d4ed8;
    margin-bottom: 1rem;
    font-weight: 700;
    font-size: 1.2rem;
}

.dark .tips-box h4 {
    color: #60a5fa;
}

.tips-box ul {
    margin: 10px 0;
    padding-left: 20px;
}

.tips-box li {
    margin: 8px 0;
    color: #333;
}

.prompts-section {
    background: #f0f8ff;
    border: 2px dashed #007bff;
    border-radius: 10px;
    padding: 20px;
    margin: 20px 0;
}

/* Enhanced Plan Header */
.plan-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 2rem;
    border-radius: 15px;
    margin-bottom: 2rem;
    text-align: center;
}

.meta-info {
    background: rgba(255,255,255,0.1);
    padding: 1rem;
    border-radius: 10px;
    margin-top: 1rem;
}

/* Enhanced Markdown Styling */
#plan_result {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
    line-height: 1.7;
    color: #2d3748;
}

#plan_result h1 {
    font-size: 2.5rem;
    font-weight: 700;
    color: #1a202c;
    margin-top: 2rem;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 3px solid #4299e1;
}

#plan_result h2 {
    font-size: 2rem;
    font-weight: 600;
    color: #2d3748;
    margin-top: 2rem;
    margin-bottom: 1rem;
    padding-bottom: 0.3rem;
    border-bottom: 2px solid #68d391;
    position: relative;
}

#plan_result h2::before {
    content: "";
    position: absolute;
    left: 0;
    bottom: -2px;
    width: 50px;
    height: 2px;
    background: linear-gradient(90deg, #4299e1, #68d391);
}

#plan_result h3 {
    font-size: 1.5rem;
    font-weight: 600;
    color: #4a5568;
    margin-top: 1.5rem;
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    padding: 0.5rem 1rem;
    background: linear-gradient(90deg, #f7fafc, #edf2f7);
    border-left: 4px solid #4299e1;
    border-radius: 0.5rem;
}

#plan_result h4 {
    font-size: 1.25rem;
    font-weight: 600;
    color: #5a67d8;
    margin-top: 1.25rem;
    margin-bottom: 0.5rem;
    padding-left: 1rem;
    border-left: 3px solid #5a67d8;
}

#plan_result h5, #plan_result h6 {
    font-size: 1.1rem;
    font-weight: 600;
    color: #667eea;
    margin-top: 1rem;
    margin-bottom: 0.5rem;
}

#plan_result p {
    margin-bottom: 1rem;
    font-size: 1rem;
    line-height: 1.8;
}

#plan_result ul, #plan_result ol {
    margin: 1rem 0;
    padding-left: 2rem;
}

#plan_result li {
    margin-bottom: 0.5rem;
    line-height: 1.7;
}

#plan_result ul li {
    list-style-type: none;
    position: relative;
}

#plan_result ul li:before {
    content: "▶";
    color: #4299e1;
    font-weight: bold;
    position: absolute;
    left: -1.5rem;
}

#plan_result blockquote {
    border-left: 4px solid #4299e1;
    background: #ebf8ff;
    padding: 1rem 1.5rem;
    margin: 1.5rem 0;
    border-radius: 0.5rem;
    font-style: italic;
    color: #2b6cb0;
}

#plan_result code {
    background: #f7fafc;
    border: 1px solid #e2e8f0;
    border-radius: 0.25rem;
    padding: 0.125rem 0.375rem;
    font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
    font-size: 0.875rem;
    color: #d53f8c;
}

#plan_result pre {
    background: #1a202c;
    color: #f7fafc;
    border-radius: 0.5rem;
    padding: 1.5rem;
    margin: 1.5rem 0;
    overflow-x: auto;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

#plan_result pre code {
    background: transparent;
    border: none;
    padding: 0;
    color: #f7fafc;
    font-size: 0.9rem;
}

#plan_result table {
    width: 100%;
    border-collapse: collapse;
    margin: 1.5rem 0;
    background: white;
    border-radius: 0.5rem;
    overflow: hidden;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

#plan_result th {
    background: #4299e1;
    color: white;
    padding: 0.75rem 1rem;
    text-align: left;
    font-weight: 600;
}

#plan_result td {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #e2e8f0;
}

#plan_result tr:nth-child(even) {
    background: #f7fafc;
}

#plan_result tr:hover {
    background: #ebf8ff;
}

#plan_result strong {
    color: #2d3748;
    font-weight: 600;
}

#plan_result em {
    color: #5a67d8;
    font-style: italic;
}

#plan_result hr {
    border: none;
    height: 2px;
    background: linear-gradient(90deg, #4299e1 0%, #68d391 100%);
    margin: 2rem 0;
    border-radius: 1px;
}

/* Special styling for reference info */
.reference-info {
    background: linear-gradient(135deg, #f0f8ff 0%, #e6f3ff 100%);
    border: 2px solid #4299e1;
    border-radius: 1rem;
    padding: 1.5rem;
    margin: 1.5rem 0;
    box-shadow: 0 4px 15px rgba(66, 153, 225, 0.1);
}

/* Special styling for prompts section */
#plan_result .prompts-highlight {
    background: linear-gradient(135deg, #f0f8ff 0%, #e6f3ff 100%);
    border: 2px solid #4299e1;
    border-radius: 1rem;
    padding: 1.5rem;
    margin: 1.5rem 0;
    position: relative;
}

#plan_result .prompts-highlight:before {
    content: "🤖";
    position: absolute;
    top: -0.5rem;
    left: 1rem;
    background: #4299e1;
    color: white;
    padding: 0.5rem;
    border-radius: 50%;
    font-size: 1.2rem;
}

/* Improved section dividers */
#plan_result .section-divider {
    background: linear-gradient(90deg, transparent 0%, #4299e1 20%, #68d391 80%, transparent 100%);
    height: 1px;
    margin: 2rem 0;
}

/* 编程提示词专用样式 */
.prompts-highlight {
    background: linear-gradient(135deg, #f0f8ff 0%, #e6f3ff 100%);
    border: 2px solid #4299e1;
    border-radius: 1rem;
    padding: 2rem;
    margin: 2rem 0;
    position: relative;
    box-shadow: 0 8px 25px rgba(66, 153, 225, 0.15);
}

.prompts-highlight:before {
    content: "🤖";
    position: absolute;
    top: -0.8rem;
    left: 1.5rem;
    background: linear-gradient(135deg, #4299e1, #667eea);
    color: white;
    padding: 0.8rem;
    border-radius: 50%;
    font-size: 1.5rem;
    box-shadow: 0 4px 12px rgba(66, 153, 225, 0.3);
}

.prompt-section {
    background: rgba(255, 255, 255, 0.8);
    border-radius: 0.8rem;
    padding: 1.5rem;
    margin: 1.5rem 0;
    border-left: 4px solid #667eea;
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.05);
}

.prompt-code-block {
    position: relative;
    margin: 1rem 0;
}

.prompt-code-block pre {
    background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%) !important;
    border: 2px solid #4299e1;
    border-radius: 0.8rem;
    padding: 1.5rem;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    position: relative;
    overflow-x: auto;
}

.prompt-code-block pre:before {
    content: "📋 点击复制此提示词";
    position: absolute;
    top: -0.5rem;
    right: 1rem;
    background: linear-gradient(45deg, #667eea, #764ba2);
    color: white;
    padding: 0.3rem 0.8rem;
    border-radius: 1rem;
    font-size: 0.8rem;
    font-weight: 500;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.prompt-code-block code {
    color: #e2e8f0 !important;
    font-family: 'Fira Code', 'Monaco', 'Consolas', monospace !important;
    font-size: 0.95rem !important;
    line-height: 1.6 !important;
    background: transparent !important;
    border: none !important;
}

/* 提示词高亮关键词 */
.prompt-code-block code .keyword {
    color: #81e6d9 !important;
    font-weight: 600;
}

.prompt-code-block code .requirement {
    color: #fbb6ce !important;
}

.prompt-code-block code .output {
    color: #c6f6d5 !important;
}

/* 优化按钮样式 */
.optimize-btn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    margin-right: 10px !important;
    transition: all 0.3s ease !important;
    padding: 0.6rem 1.2rem !important;
    border-radius: 1.5rem !important;
}

.optimize-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4) !important;
}

.reset-btn {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    padding: 0.6rem 1.2rem !important;
    border-radius: 1.5rem !important;
}

.reset-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(240, 147, 251, 0.4) !important;
}

.optimization-result {
    margin-top: 15px !important;
    padding: 15px !important;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border-radius: 8px !important;
    color: white !important;
    border-left: 4px solid #4facfe !important;
}

.optimization-result h2 {
    color: #fff !important;
    margin-bottom: 10px !important;
}

.optimization-result strong {
    color: #e0e6ff !important;
}

/* 处理过程说明区域样式 */
.process-explanation {
    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%) !important;
    border: 2px solid #cbd5e0 !important;
    border-radius: 1rem !important;
    padding: 2rem !important;
    margin: 1rem 0 !important;
    font-family: 'Inter', -apple-system, system-ui, sans-serif !important;
}

.process-explanation h1 {
    color: #2b6cb0 !important;
    font-size: 1.8rem !important;
    margin-bottom: 1rem !important;
    border-bottom: 3px solid #3182ce !important;
    padding-bottom: 0.5rem !important;
}

.process-explanation h2 {
    color: #2c7a7b !important;
    font-size: 1.4rem !important;
    margin-top: 1.5rem !important;
    margin-bottom: 1rem !important;
    background: linear-gradient(135deg, #e6fffa 0%, #f0fff4 100%) !important;
    padding: 0.8rem !important;
    border-radius: 0.5rem !important;
    border-left: 4px solid #38b2ac !important;
}

.process-explanation h3 {
    color: #38a169 !important;
    font-size: 1.2rem !important;
    margin-top: 1rem !important;
    margin-bottom: 0.5rem !important;
}

.process-explanation strong {
    color: #e53e3e !important;
    font-weight: 600 !important;
}

.process-explanation ul {
    padding-left: 1.5rem !important;
}

.process-explanation li {
    margin-bottom: 0.5rem !important;
    color: #4a5568 !important;
}

.explanation-btn {
    background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    padding: 0.6rem 1.2rem !important;
    border-radius: 1.5rem !important;
    margin-right: 10px !important;
}

.explanation-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(66, 153, 225, 0.4) !important;
}

/* 复制按钮增强 */
.copy-btn {
    background: linear-gradient(45deg, #667eea, #764ba2) !important;
    border: none !important;
    color: white !important;
    padding: 0.8rem 1.5rem !important;
    border-radius: 2rem !important;
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3) !important;
}

.copy-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4) !important;
    background: linear-gradient(45deg, #5a67d8, #667eea) !important;
}

.copy-btn:active {
    transform: translateY(0) !important;
}

/* 响应式优化 */
@media (max-width: 768px) {
    .main-container {
        max-width: 100%;
        padding: 10px;
    }
    
    .prompts-highlight {
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .prompt-section {
        padding: 1rem;
    }
    
    .prompt-code-block pre {
        padding: 1rem;
        font-size: 0.85rem;
    }
    
    .prompt-copy-section {
        margin: 0.5rem 0;
        padding: 0.25rem;
        flex-direction: column;
        align-items: stretch;
    }
    
    .individual-copy-btn {
        width: 100% !important;
        justify-content: center !important;
        margin: 0.25rem 0 !important;
        padding: 0.5rem 1rem !important;
        font-size: 0.8rem !important;
    }
    
    #plan_result h1 {
        font-size: 2rem;
    }
    
    #plan_result h2 {
        font-size: 1.5rem;
    }
    
    #plan_result h3 {
        font-size: 1.25rem;
        padding: 0.375rem 0.75rem;
    }
}

@media (max-width: 1024px) and (min-width: 769px) {
    .main-container {
        max-width: 95%;
        padding: 15px;
    }
    
    .individual-copy-btn {
        padding: 0.45rem 0.9rem !important;
        font-size: 0.78rem !important;
    }
    
    .prompt-copy-section {
        margin: 0.6rem 0;
    }
}

/* Mermaid图表样式优化 */
.mermaid {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%) !important;
    border: 2px solid #3b82f6 !important;
    border-radius: 1rem !important;
    padding: 2rem !important;
    margin: 2rem 0 !important;
    text-align: center !important;
    box-shadow: 0 8px 25px rgba(59, 130, 246, 0.15) !important;
}

.dark .mermaid {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
    border-color: #60a5fa !important;
    color: #f8fafc !important;
}

/* Mermaid包装器样式 */
.mermaid-wrapper {
    margin: 2rem 0;
    position: relative;
    overflow: hidden;
    border-radius: 1rem;
    background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
    border: 2px solid #3b82f6;
    box-shadow: 0 10px 30px rgba(59, 130, 246, 0.2);
}

.mermaid-render {
    min-height: 200px;
    padding: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
}

.dark .mermaid-wrapper {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-color: #60a5fa;
}

/* 图表错误处理 */
.mermaid-error {
    background: #fef2f2;
    border: 2px solid #f87171;
    color: #991b1b;
    padding: 1rem;
    border-radius: 0.5rem;
    text-align: center;
    font-family: monospace;
}

.dark .mermaid-error {
    background: #7f1d1d;
    border-color: #ef4444;
    color: #fecaca;
}

/* Mermaid图表容器增强 */
.chart-container {
    background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
    border: 3px solid #3b82f6;
    border-radius: 1.5rem;
    padding: 2rem;
    margin: 2rem 0;
    text-align: center;
    position: relative;
    box-shadow: 0 10px 30px rgba(59, 130, 246, 0.2);
}

.chart-container::before {
    content: "📊";
    position: absolute;
    top: -1rem;
    left: 2rem;
    background: linear-gradient(135deg, #3b82f6, #1d4ed8);
    color: white;
    padding: 0.8rem;
    border-radius: 50%;
    font-size: 1.5rem;
    box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
}

.dark .chart-container {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-color: #60a5fa;
}

.dark .chart-container::before {
    background: linear-gradient(135deg, #60a5fa, #3b82f6);
}

/* 表格样式全面增强 */
.enhanced-table {
    width: 100%;
    border-collapse: collapse;
    margin: 2rem 0;
    background: white;
    border-radius: 1rem;
    overflow: hidden;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
    border: 2px solid #e5e7eb;
}

.enhanced-table th {
    background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
    color: white;
    padding: 1.2rem;
    text-align: left;
    font-weight: 700;
    font-size: 1rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.enhanced-table td {
    padding: 1rem 1.2rem;
    border-bottom: 1px solid #e5e7eb;
    vertical-align: top;
    font-size: 0.95rem;
    line-height: 1.6;
}

.enhanced-table tr:nth-child(even) {
    background: linear-gradient(90deg, #f8fafc 0%, #f1f5f9 100%);
}

.enhanced-table tr:hover {
    background: linear-gradient(90deg, #eff6ff 0%, #dbeafe 100%);
    transform: translateY(-1px);
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(59, 130, 246, 0.1);
}

.dark .enhanced-table {
    background: #1f2937;
    border-color: #374151;
}

.dark .enhanced-table th {
    background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
    color: #f9fafb;
}

.dark .enhanced-table td {
    border-bottom-color: #374151;
    color: #f9fafb;
}

.dark .enhanced-table tr:nth-child(even) {
    background: linear-gradient(90deg, #374151 0%, #1f2937 100%);
}

.dark .enhanced-table tr:hover {
    background: linear-gradient(90deg, #4b5563 0%, #374151 100%);
}

/* 单独复制按钮样式 */
.prompt-copy-section {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    margin: 0.75rem 0;
    padding: 0.375rem;
    background: rgba(66, 153, 225, 0.05);
    border-radius: 0.375rem;
}

.individual-copy-btn {
    background: linear-gradient(45deg, #4299e1, #3182ce) !important;
    border: none !important;
    color: white !important;
    padding: 0.4rem 0.8rem !important;
    border-radius: 0.75rem !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 1px 4px rgba(66, 153, 225, 0.2) !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 0.25rem !important;
    min-width: auto !important;
    max-height: 32px !important;
}

.individual-copy-btn:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 2px 8px rgba(66, 153, 225, 0.3) !important;
    background: linear-gradient(45deg, #3182ce, #2c5aa0) !important;
}

.individual-copy-btn:active {
    transform: translateY(0) !important;
}

.edit-prompt-btn {
    background: linear-gradient(45deg, #667eea, #764ba2) !important;
    border: none !important;
    color: white !important;
    padding: 0.4rem 0.8rem !important;
    border-radius: 0.75rem !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 1px 4px rgba(102, 126, 234, 0.2) !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 0.25rem !important;
    min-width: auto !important;
    max-height: 32px !important;
    margin-left: 0.5rem !important;
}

.edit-prompt-btn:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3) !important;
    background: linear-gradient(45deg, #5a67d8, #667eea) !important;
}

.edit-prompt-btn:active {
    transform: translateY(0) !important;
}

.copy-success-msg {
    font-size: 0.85rem;
    font-weight: 600;
    animation: fadeInOut 2s ease-in-out;
}

@keyframes fadeInOut {
    0% { opacity: 0; transform: translateX(-10px); }
    20% { opacity: 1; transform: translateX(0); }
    80% { opacity: 1; transform: translateX(0); }
    100% { opacity: 0; transform: translateX(10px); }
}

.dark .prompt-copy-section {
    background: rgba(99, 179, 237, 0.1);
}

.dark .individual-copy-btn {
    background: linear-gradient(45deg, #63b3ed, #4299e1) !important;
    box-shadow: 0 1px 4px rgba(99, 179, 237, 0.2) !important;
}

.dark .individual-copy-btn:hover {
    background: linear-gradient(45deg, #4299e1, #3182ce) !important;
    box-shadow: 0 2px 8px rgba(99, 179, 237, 0.3) !important;
}

.dark .edit-prompt-btn {
    background: linear-gradient(45deg, #9f7aea, #805ad5) !important;
    box-shadow: 0 1px 4px rgba(159, 122, 234, 0.2) !important;
}

.dark .edit-prompt-btn:hover {
    background: linear-gradient(45deg, #805ad5, #6b46c1) !important;
    box-shadow: 0 2px 8px rgba(159, 122, 234, 0.3) !important;
}

/* Fix accordion height issue - Agent应用架构说明折叠问题 */
.gradio-accordion {
    transition: all 0.3s ease !important;
    overflow: hidden !important;
}

.gradio-accordion[data-testid$="accordion"] {
    min-height: auto !important;
    height: auto !important;
}

.gradio-accordion .gradio-accordion-content {
    transition: max-height 0.3s ease !important;
    overflow: hidden !important;
}

/* Gradio内部accordion组件修复 */
details.gr-accordion {
    transition: all 0.3s ease !important;
}

details.gr-accordion[open] {
    height: auto !important;
    min-height: auto !important;
}

details.gr-accordion:not([open]) {
    height: auto !important;
    min-height: 50px !important;
}

/* 确保折叠后页面恢复正常大小 */
.gr-block.gr-box {
    transition: height 0.3s ease !important;
    height: auto !important;
}

/* Fix for quick start text contrast */
#quick_start_container p {
    color: #4A5568;
}

.dark #quick_start_container p {
    color: #E2E8F0;
}

/* 重要：大幅改善dark模式下的文字对比度 */

/* 主要内容区域 - AI生成内容显示区 */
.dark #plan_result {
    color: #F7FAFC !important;
    background: #2D3748 !important;
}

.dark #plan_result p {
    color: #F7FAFC !important;
}

.dark #plan_result strong {
    color: #FFFFFF !important;
}

/* Dark模式下占位符样式优化 */
.dark #plan_result div[style*="background: linear-gradient"] {
    background: linear-gradient(135deg, #2D3748 0%, #4A5568 100%) !important;
    border-color: #63B3ED !important;
}

.dark #plan_result h3 {
    color: #63B3ED !important;
}

.dark #plan_result div[style*="background: linear-gradient(90deg"] {
    background: linear-gradient(90deg, #2D3748 0%, #1A202C 100%) !important;
    border-left-color: #4FD1C7 !important;
}

.dark #plan_result div[style*="background: linear-gradient(45deg"] {
    background: linear-gradient(45deg, #4A5568 0%, #2D3748 100%) !important;
}

/* Dark模式下的彩色文字优化 */
.dark #plan_result span[style*="color: #e53e3e"] {
    color: #FC8181 !important;
}

.dark #plan_result span[style*="color: #38a169"] {
    color: #68D391 !important;
}

.dark #plan_result span[style*="color: #3182ce"] {
    color: #63B3ED !important;
}

.dark #plan_result span[style*="color: #805ad5"] {
    color: #B794F6 !important;
}

.dark #plan_result strong[style*="color: #d69e2e"] {
    color: #F6E05E !important;
}

.dark #plan_result strong[style*="color: #e53e3e"] {
    color: #FC8181 !important;
}

.dark #plan_result p[style*="color: #2c7a7b"] {
    color: #4FD1C7 !important;
}

.dark #plan_result p[style*="color: #c53030"] {
    color: #FC8181 !important;
}

/* 重点优化：AI编程助手使用说明区域 */
.dark #ai_helper_instructions {
    color: #F7FAFC !important;
    background: rgba(45, 55, 72, 0.8) !important;
}

.dark #ai_helper_instructions p {
    color: #F7FAFC !important;
}

.dark #ai_helper_instructions li {
    color: #F7FAFC !important;
}

.dark #ai_helper_instructions strong {
    color: #FFFFFF !important;
}

/* 生成内容的markdown渲染 - 主要问题区域 */
.dark #plan_result {
    color: #FFFFFF !important;
    background: #1A202C !important;
}

.dark #plan_result h1,
.dark #plan_result h2,
.dark #plan_result h3,
.dark #plan_result h4,
.dark #plan_result h5,
.dark #plan_result h6 {
    color: #FFFFFF !important;
}

.dark #plan_result p {
    color: #FFFFFF !important;
}

.dark #plan_result li {
    color: #FFFFFF !important;
}

.dark #plan_result strong {
    color: #FFFFFF !important;
}

.dark #plan_result em {
    color: #E2E8F0 !important;
}

.dark #plan_result td {
    color: #FFFFFF !important;
    background: #2D3748 !important;
}

.dark #plan_result th {
    color: #FFFFFF !important;
    background: #1A365D !important;
}

/* 确保所有文字内容都是白色 */
.dark #plan_result * {
    color: #FFFFFF !important;
}

/* 特殊元素保持样式 */
.dark #plan_result code {
    color: #81E6D9 !important;
    background: #1A202C !important;
}

.dark #plan_result pre {
    background: #0D1117 !important;
    color: #F0F6FC !important;
}

.dark #plan_result blockquote {
    color: #FFFFFF !important;
    background: #2D3748 !important;
    border-left-color: #63B3ED !important;
}

/* 确保生成报告在dark模式下清晰可见 */
.dark .plan-header {
    background: linear-gradient(135deg, #4A5568 0%, #2D3748 100%) !important;
    color: #FFFFFF !important;
}

.dark .meta-info {
    background: rgba(255,255,255,0.2) !important;
    color: #FFFFFF !important;
}

/* 提示词容器在dark模式下的优化 */
.dark .prompts-highlight {
    background: linear-gradient(135deg, #2D3748 0%, #4A5568 100%) !important;
    border: 2px solid #63B3ED !important;
    color: #F7FAFC !important;
}

.dark .prompt-section {
    background: rgba(45, 55, 72, 0.9) !important;
    color: #F7FAFC !important;
    border-left: 4px solid #63B3ED !important;
}

/* 确保所有文字内容在dark模式下都清晰可见 */
.dark textarea,
.dark input {
    color: #F7FAFC !important;
    background: #2D3748 !important;
}

.dark .gr-markdown {
    color: #F7FAFC !important;
}

/* 特别针对提示文字的优化 */
.dark .tips-box {
    background: #2D3748 !important;
    color: #F7FAFC !important;
}

.dark .tips-box h4 {
    color: #63B3ED !important;
}

.dark .tips-box li {
    color: #F7FAFC !important;
}

/* 按钮在dark模式下的优化 */
.dark .copy-btn {
    color: #FFFFFF !important;
}

/* 确保Agent应用说明在dark模式下清晰 */
.dark .gr-accordion {
    color: #F7FAFC !important;
    background: #2D3748 !important;
}

/* 修复具体的文字对比度问题 */
.dark #input_idea_title {
    color: #FFFFFF !important;
}

.dark #input_idea_title h2 {
    color: #FFFFFF !important;
}

.dark #download_success_info {
    background: #2D3748 !important;
    color: #F7FAFC !important;
    border: 1px solid #4FD1C7 !important;
}

.dark #download_success_info strong {
    color: #68D391 !important;
}

.dark #download_success_info span {
    color: #F7FAFC !important;
}

.dark #usage_tips {
    background: #2D3748 !important;
    color: #F7FAFC !important;
    border: 1px solid #63B3ED !important;
}

.dark #usage_tips strong {
    color: #63B3ED !important;
}

/* Loading spinner */
.loading-spinner {
    border: 3px solid #f3f3f3;
    border-top: 3px solid #007bff;
    border-radius: 50%;
    width: 20px;
    height: 20px;
    animation: spin 1s linear infinite;
    display: inline-block;
    margin-right: 10px;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Copy buttons styling */
.copy-buttons {
    display: flex;
    gap: 10px;
    margin: 1rem 0;
}

.copy-btn {
    background: linear-gradient(45deg, #28a745, #20c997) !important;
    border: none !important;
    color: white !important;
    padding: 8px 16px !important;
    border-radius: 20px !important;
    font-size: 14px !important;
    transition: all 0.3s ease !important;
}

.copy-btn:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3) !important;
}

/* 分段编辑器样式 */
.plan-editor-container {
    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
    border: 2px solid #cbd5e0;
    border-radius: 1rem;
    padding: 2rem;
    margin: 2rem 0;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.editor-header {
    text-align: center;
    margin-bottom: 2rem;
    padding-bottom: 1rem;
    border-bottom: 2px solid #e2e8f0;
}

.editor-header h3 {
    color: #2b6cb0;
    margin-bottom: 0.5rem;
    font-size: 1.5rem;
    font-weight: 700;
}

.editor-header p {
    color: #4a5568;
    margin: 0;
    font-size: 1rem;
}

.sections-container {
    display: grid;
    gap: 1.5rem;
    margin-bottom: 2rem;
}

.editable-section {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 0.75rem;
    padding: 1.5rem;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.editable-section:hover {
    border-color: #3b82f6;
    box-shadow: 0 4px 15px rgba(59, 130, 246, 0.1);
    transform: translateY(-2px);
}

.section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #f1f5f9;
}

.section-type {
    font-size: 1.2rem;
    margin-right: 0.5rem;
}

.section-title {
    font-weight: 600;
    color: #2d3748;
    flex: 1;
}

.edit-section-btn {
    background: linear-gradient(45deg, #667eea, #764ba2) !important;
    border: none !important;
    color: white !important;
    padding: 0.5rem 1rem !important;
    border-radius: 0.5rem !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2) !important;
}

.edit-section-btn:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3) !important;
    background: linear-gradient(45deg, #5a67d8, #667eea) !important;
}

.section-preview {
    position: relative;
}

.preview-content {
    color: #4a5568;
    line-height: 1.6;
    font-size: 0.95rem;
    padding: 1rem;
    background: #f8fafc;
    border-radius: 0.5rem;
    border-left: 4px solid #3b82f6;
}

.editor-actions {
    display: flex;
    gap: 1rem;
    justify-content: center;
    align-items: center;
    padding-top: 1.5rem;
    border-top: 2px solid #e2e8f0;
}

.apply-changes-btn {
    background: linear-gradient(45deg, #48bb78, #38a169) !important;
    border: none !important;
    color: white !important;
    padding: 0.8rem 1.5rem !important;
    border-radius: 0.75rem !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(72, 187, 120, 0.3) !important;
}

.apply-changes-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(72, 187, 120, 0.4) !important;
    background: linear-gradient(45deg, #38a169, #2f855a) !important;
}

.reset-changes-btn {
    background: linear-gradient(45deg, #f093fb, #f5576c) !important;
    border: none !important;
    color: white !important;
    padding: 0.8rem 1.5rem !important;
    border-radius: 0.75rem !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(240, 147, 251, 0.3) !important;
}

.reset-changes-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(240, 147, 251, 0.4) !important;
    background: linear-gradient(45deg, #f5576c, #e53e3e) !important;
}

/* 编辑历史样式 */
.edit-history {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 0.75rem;
    padding: 1.5rem;
    margin: 1rem 0;
}

.edit-history h3 {
    color: #2b6cb0;
    margin-bottom: 1rem;
    font-size: 1.25rem;
}

.history-list {
    max-height: 300px;
    overflow-y: auto;
}

.history-item {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 0.5rem;
    padding: 1rem;
    margin-bottom: 0.75rem;
    transition: all 0.2s ease;
}

.history-item:hover {
    border-color: #3b82f6;
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
}

.history-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0.5rem;
    font-size: 0.9rem;
}

.history-index {
    background: #3b82f6;
    color: white;
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    font-weight: 600;
    font-size: 0.8rem;
}

.history-time {
    color: #6b7280;
    font-family: 'Monaco', monospace;
}

.history-section {
    color: #4a5568;
    font-weight: 500;
}

.history-comment {
    color: #374151;
    font-style: italic;
    padding-left: 1rem;
    border-left: 2px solid #e5e7eb;
}

/* Dark模式适配 */
.dark .plan-editor-container {
    background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
    border-color: #4a5568;
}

.dark .editor-header h3 {
    color: #63b3ed;
}

.dark .editor-header p {
    color: #e2e8f0;
}

.dark .editable-section {
    background: #374151;
    border-color: #4a5568;
}

.dark .editable-section:hover {
    border-color: #60a5fa;
}

.dark .section-title {
    color: #f7fafc;
}

.dark .preview-content {
    color: #e2e8f0;
    background: #2d3748;
    border-left-color: #60a5fa;
}

.dark .edit-history {
    background: #2d3748;
    border-color: #4a5568;
}

.dark .edit-history h3 {
    color: #63b3ed;
}

.dark .history-item {
    background: #374151;
    border-color: #4a5568;
}

.dark .history-item:hover {
    border-color: #60a5fa;
}

.dark .history-time {
    color: #9ca3af;
}

.dark .history-section {
    color: #e2e8f0;
}

.dark .history-comment {
    color: #d1d5db;
    border-left-color: #4a5568;
}

/* 响应式设计 */
@media (max-width: 768px) {
    .plan-editor-container {
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .section-header {
        flex-direction: column;
        gap: 0.5rem;
        align-items: flex-start;
    }
    
    .edit-section-btn {
        align-self: flex-end;
    }
    
    .editor-actions {
        flex-direction: column;
        gap: 0.75rem;
    }
    
    .apply-changes-btn,
    .reset-changes-btn {
        width: 100%;
    }
}
"""

# 保持美化的Gradio界面
with gr.Blocks(
    title="VibeDoc Agent：您的随身AI产品经理与架构师",
    theme=gr.themes.Soft(primary_hue="blue"),
    css=custom_css
) as demo:
    
    gr.HTML("""
    <div class="header-gradient">
        <h1>🚀 VibeDoc - AI-Powered Development Plan Generator</h1>
        <p style="font-size: 18px; margin: 15px 0; opacity: 0.95;">
            🤖 Transform your ideas into comprehensive development plans in 60-180 seconds
        </p>
        <p style="opacity: 0.85;">
            ✨ AI-Driven Planning | � Visual Diagrams | 🎯 Professional Output | � Multi-format Export
        </p>
        <div style="margin-top: 1rem; padding: 0.5rem; background: rgba(255,255,255,0.1); border-radius: 0.5rem;">
            <small style="opacity: 0.9;">
                🌟 Open Source Project | 💡 Built with Qwen2.5-72B-Instruct | ⚡ Fast & Reliable
            </small>
        </div>
    </div>
    
    <!-- 添加Mermaid.js支持 -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
        // 增强的Mermaid配置
        mermaid.initialize({ 
            startOnLoad: true,
            theme: 'default',
            flowchart: {
                useMaxWidth: true,
                htmlLabels: true,
                curve: 'basis'
            },
            gantt: {
                useMaxWidth: true,
                gridLineStartPadding: 350,
                fontSize: 13,
                fontFamily: '"Inter", "Source Sans Pro", sans-serif',
                sectionFontSize: 24,
                numberSectionStyles: 4
            },
            themeVariables: {
                primaryColor: '#3b82f6',
                primaryTextColor: '#1f2937',
                primaryBorderColor: '#1d4ed8',
                lineColor: '#6b7280',
                secondaryColor: '#dbeafe',
                tertiaryColor: '#f8fafc',
                background: '#ffffff',
                mainBkg: '#ffffff',
                secondBkg: '#f1f5f9',
                tertiaryBkg: '#eff6ff'
            }
        });
        
        // 监听主题变化，动态更新Mermaid主题
        function updateMermaidTheme() {
            const isDark = document.documentElement.classList.contains('dark');
            const theme = isDark ? 'dark' : 'default';
            mermaid.initialize({ 
                startOnLoad: true,
                theme: theme,
                flowchart: {
                    useMaxWidth: true,
                    htmlLabels: true,
                    curve: 'basis'
                },
                gantt: {
                    useMaxWidth: true,
                    gridLineStartPadding: 350,
                    fontSize: 13,
                    fontFamily: '"Inter", "Source Sans Pro", sans-serif',
                    sectionFontSize: 24,
                    numberSectionStyles: 4
                },
                themeVariables: isDark ? {
                    primaryColor: '#60a5fa',
                    primaryTextColor: '#f8fafc',
                    primaryBorderColor: '#3b82f6',
                    lineColor: '#94a3b8',
                    secondaryColor: '#1e293b',
                    tertiaryColor: '#0f172a',
                    background: '#1f2937',
                    mainBkg: '#1f2937',
                    secondBkg: '#374151',
                    tertiaryBkg: '#1e293b'
                } : {
                    primaryColor: '#3b82f6',
                    primaryTextColor: '#1f2937',
                    primaryBorderColor: '#1d4ed8',
                    lineColor: '#6b7280',
                    secondaryColor: '#dbeafe',
                    tertiaryColor: '#f8fafc',
                    background: '#ffffff',
                    mainBkg: '#ffffff',
                    secondBkg: '#f1f5f9',
                    tertiaryBkg: '#eff6ff'
                }
            });
            
            // 重新渲染所有Mermaid图表
            renderMermaidCharts();
        }
        
        // 强化的Mermaid图表渲染函数
        function renderMermaidCharts() {
            try {
                // 清除现有的渲染内容
                document.querySelectorAll('.mermaid').forEach(element => {
                    if (element.getAttribute('data-processed') !== 'true') {
                        element.removeAttribute('data-processed');
                    }
                });
                
                // 处理包装器中的Mermaid内容
                document.querySelectorAll('.mermaid-render').forEach(element => {
                    const content = element.textContent.trim();
                    if (content && !element.classList.contains('rendered')) {
                        element.innerHTML = content;
                        element.classList.add('mermaid', 'rendered');
                    }
                });
                
                // 重新初始化Mermaid
                mermaid.init(undefined, document.querySelectorAll('.mermaid:not([data-processed="true"])'));
                
            } catch (error) {
                console.warn('Mermaid渲染警告:', error);
                // 如果渲染失败，显示错误信息
                document.querySelectorAll('.mermaid-render').forEach(element => {
                    if (!element.classList.contains('rendered')) {
                        element.innerHTML = '<div class="mermaid-error">图表渲染中，请稍候...</div>';
                    }
                });
            }
        }
        
        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(renderMermaidCharts, 1000);
        });
        
        // 监听内容变化，自动重新渲染图表
        function observeContentChanges() {
            const observer = new MutationObserver(function(mutations) {
                let shouldRender = false;
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'childList') {
                        mutation.addedNodes.forEach(function(node) {
                            if (node.nodeType === Node.ELEMENT_NODE) {
                                if (node.classList && (node.classList.contains('mermaid') || node.querySelector('.mermaid'))) {
                                    shouldRender = true;
                                }
                            }
                        });
                    }
                });
                
                if (shouldRender) {
                    setTimeout(renderMermaidCharts, 500);
                }
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        }
        
        // 启动内容观察器
        observeContentChanges();
        
        // 单独复制提示词功能
        function copyIndividualPrompt(promptId, promptContent) {
            // 解码HTML实体
            const decodedContent = promptContent.replace(/\\n/g, '\n').replace(/\\'/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
            
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(decodedContent).then(() => {
                    showCopySuccess(promptId);
                }).catch(err => {
                    console.error('复制失败:', err);
                    fallbackCopy(decodedContent);
                });
            } else {
                fallbackCopy(decodedContent);
            }
        }
        
        // 编辑提示词功能
        function editIndividualPrompt(promptId, promptContent) {
            // 解码HTML实体
            const decodedContent = promptContent.replace(/\\n/g, '\n').replace(/\\'/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
            
            // 检测当前主题
            const isDark = document.documentElement.classList.contains('dark');
            
            // 创建编辑对话框
            const editDialog = document.createElement('div');
            editDialog.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 10000;
            `;
            
            editDialog.innerHTML = `
                <div style="
                    background: ${isDark ? '#2d3748' : 'white'};
                    color: ${isDark ? '#f7fafc' : '#2d3748'};
                    padding: 2rem;
                    border-radius: 1rem;
                    max-width: 80%;
                    max-height: 80%;
                    overflow-y: auto;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                ">
                    <h3 style="margin-bottom: 1rem; color: ${isDark ? '#f7fafc' : '#2d3748'};">✏️ 编辑提示词</h3>
                    <textarea
                        id="prompt-editor-${promptId}"
                        style="
                            width: 100%;
                            height: 300px;
                            padding: 1rem;
                            border: 2px solid ${isDark ? '#4a5568' : '#e2e8f0'};
                            border-radius: 0.5rem;
                            font-family: 'Fira Code', monospace;
                            font-size: 0.9rem;
                            resize: vertical;
                            line-height: 1.5;
                            background: ${isDark ? '#1a202c' : 'white'};
                            color: ${isDark ? '#f7fafc' : '#2d3748'};
                        "
                        placeholder="在此编辑您的提示词..."
                    >${decodedContent}</textarea>
                    <div style="margin-top: 1rem; display: flex; gap: 1rem; justify-content: flex-end;">
                        <button
                            id="cancel-edit-${promptId}"
                            style="
                                padding: 0.5rem 1rem;
                                border: 1px solid ${isDark ? '#4a5568' : '#cbd5e0'};
                                background: ${isDark ? '#2d3748' : 'white'};
                                color: ${isDark ? '#f7fafc' : '#4a5568'};
                                border-radius: 0.5rem;
                                cursor: pointer;
                                transition: all 0.2s ease;
                            "
                        >取消</button>
                        <button
                            id="save-edit-${promptId}"
                            style="
                                padding: 0.5rem 1rem;
                                background: linear-gradient(45deg, #667eea, #764ba2);
                                color: white;
                                border: none;
                                border-radius: 0.5rem;
                                cursor: pointer;
                                transition: all 0.2s ease;
                            "
                        >保存并复制</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(editDialog);
            
            // 绑定按钮事件
            document.getElementById(`cancel-edit-${promptId}`).addEventListener('click', () => {
                document.body.removeChild(editDialog);
            });
            
            document.getElementById(`save-edit-${promptId}`).addEventListener('click', () => {
                const editedContent = document.getElementById(`prompt-editor-${promptId}`).value;
                
                // 复制编辑后的内容
                if (navigator.clipboard && window.isSecureContext) {
                    navigator.clipboard.writeText(editedContent).then(() => {
                        showCopySuccess(promptId);
                        document.body.removeChild(editDialog);
                    }).catch(err => {
                        console.error('复制失败:', err);
                        fallbackCopy(editedContent);
                        document.body.removeChild(editDialog);
                    });
                } else {
                    fallbackCopy(editedContent);
                    document.body.removeChild(editDialog);
                }
            });
            
            // ESC键关闭
            const escapeHandler = (e) => {
                if (e.key === 'Escape') {
                    document.body.removeChild(editDialog);
                    document.removeEventListener('keydown', escapeHandler);
                }
            };
            document.addEventListener('keydown', escapeHandler);
            
            // 点击外部关闭
            editDialog.addEventListener('click', (e) => {
                if (e.target === editDialog) {
                    document.body.removeChild(editDialog);
                    document.removeEventListener('keydown', escapeHandler);
                }
            });
        }
        
        // 降级复制方案
        function fallbackCopy(text) {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                alert('✅ 提示词已复制到剪贴板！');
            } catch (err) {
                alert('❌ 复制失败，请手动选择文本复制');
            }
            document.body.removeChild(textArea);
        }
        
        // 显示复制成功提示
        function showCopySuccess(promptId) {
            const successMsg = document.getElementById('copy-success-' + promptId);
            if (successMsg) {
                successMsg.style.display = 'inline';
                setTimeout(() => {
                    successMsg.style.display = 'none';
                }, 2000);
            }
        }
        
        // 绑定复制和编辑按钮事件
        function bindCopyButtons() {
            document.querySelectorAll('.individual-copy-btn').forEach(button => {
                button.addEventListener('click', function() {
                    const promptId = this.getAttribute('data-prompt-id');
                    const promptContent = this.getAttribute('data-prompt-content');
                    copyIndividualPrompt(promptId, promptContent);
                });
            });
            
            document.querySelectorAll('.edit-prompt-btn').forEach(button => {
                button.addEventListener('click', function() {
                    const promptId = this.getAttribute('data-prompt-id');
                    const promptContent = this.getAttribute('data-prompt-content');
                    editIndividualPrompt(promptId, promptContent);
                });
            });
        }
        
        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', function() {
            updateMermaidTheme();
            bindCopyButtons();
            
            // 监听主题切换
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                        updateMermaidTheme();
                        // 重新渲染所有Mermaid图表
                        setTimeout(() => {
                            document.querySelectorAll('.mermaid').forEach(element => {
                                mermaid.init(undefined, element);
                            });
                        }, 100);
                    }
                });
            });
            observer.observe(document.documentElement, { attributes: true });
            
            // 监听内容变化，重新绑定复制按钮
            const contentObserver = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'childList') {
                        bindCopyButtons();
                    }
                });
            });
            
            // 监听plan_result区域的变化
            const planResult = document.getElementById('plan_result');
            if (planResult) {
                contentObserver.observe(planResult, { childList: true, subtree: true });
            }
        });
    </script>
    """)
    
    with gr.Row():
        with gr.Column(scale=2, elem_classes="content-card"):
            gr.Markdown("## 💡 输入您的产品创意", elem_id="input_idea_title")
            
            idea_input = gr.Textbox(
                label="产品创意描述",
                placeholder="例如：我想做一个帮助程序员管理代码片段的工具，支持多语言语法高亮，可以按标签分类，还能分享给团队成员...",
                lines=5,
                max_lines=10,
                show_label=False
            )
            
            # 优化按钮和结果显示
            with gr.Row():
                optimize_btn = gr.Button(
                    "✨ 优化创意描述",
                    variant="secondary",
                    size="sm",
                    elem_classes="optimize-btn"
                )
                reset_btn = gr.Button(
                    "🔄 重置",
                    variant="secondary", 
                    size="sm",
                    elem_classes="reset-btn"
                )
            
            optimization_result = gr.Markdown(
                visible=False,
                elem_classes="optimization-result"
            )
            
            reference_url_input = gr.Textbox(
                label="参考链接 (可选)",
                placeholder="输入任何网页链接（如博客、新闻、文档）作为参考...",
                lines=1,
                show_label=True
            )
            
            generate_btn = gr.Button(
                "🤖 AI生成开发计划 + 编程提示词",
                variant="primary",
                size="lg",
                elem_classes="generate-btn"
            )
        
        with gr.Column(scale=1):
            gr.HTML("""
            <div class="tips-box">
                <h4 style="color: #e53e3e;">💡 简单三步</h4>
                <div style="font-size: 16px; font-weight: 600; text-align: center; margin: 20px 0;">
                    <span style="color: #e53e3e;">创意描述</span> → 
                    <span style="color: #38a169;">智能分析</span> → 
                    <span style="color: #3182ce;">完整方案</span>
                </div>
                <h4 style="color: #38a169;">🎯 核心功能</h4>
                <ul>
                    <li><span style="color: #e53e3e;">📋</span> 完整开发计划</li>
                    <li><span style="color: #3182ce;">🤖</span> AI编程提示词</li>
                    <li><span style="color: #38a169;">�</span> 可视化图表</li>
                    <li><span style="color: #d69e2e;">🔗</span> MCP服务增强</li>
                </ul>
                <h4 style="color: #3182ce;">⏱️ 生成时间</h4>
                <ul>
                    <li><span style="color: #e53e3e;">✨</span> 创意优化：20秒</li>
                    <li><span style="color: #38a169;">📝</span> 方案生成：150-200秒</li>
                    <li><span style="color: #d69e2e;">⚡</span> 一键复制下载</li>
                </ul>
            </div>
            """)
    
    # 结果显示区域
    with gr.Column(elem_classes="result-container"):
        plan_output = gr.Markdown(
            value="""
<div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); border-radius: 1rem; border: 2px dashed #cbd5e0;">
    <div style="font-size: 3rem; margin-bottom: 1rem;">🤖</div>
    <h3 style="color: #2b6cb0; margin-bottom: 1rem; font-weight: bold;">智能开发计划生成</h3>
    <p style="color: #4a5568; font-size: 1.1rem; margin-bottom: 1.5rem;">
        💭 <strong style="color: #e53e3e;">输入创意，获得完整开发方案</strong>
    </p>
    <div style="background: linear-gradient(90deg, #edf2f7 0%, #e6fffa 100%); padding: 1rem; border-radius: 0.5rem; margin: 1rem 0; border-left: 4px solid #38b2ac;">
        <p style="color: #2c7a7b; margin: 0; font-weight: 600;">
            🎯 <span style="color: #e53e3e;">技术方案</span> • <span style="color: #38a169;">开发计划</span> • <span style="color: #3182ce;">编程提示词</span>
        </p>
    </div>
    <p style="color: #a0aec0; font-size: 0.9rem;">
        点击 <span style="color: #e53e3e; font-weight: bold;">"🤖 AI生成开发计划"</span> 按钮开始
    </p>
</div>
            """,
            elem_id="plan_result",
            label="AI生成的开发计划"
        )
        
        # 处理过程说明区域
        process_explanation = gr.Markdown(
            visible=False,
            elem_classes="process-explanation"
        )
        
        # 切换按钮
        with gr.Row():
            show_explanation_btn = gr.Button(
                "🔍 查看AI生成过程详情",
                variant="secondary",
                size="sm",
                elem_classes="explanation-btn",
                visible=False
            )
            hide_explanation_btn = gr.Button(
                "📝 返回开发计划",
                variant="secondary",
                size="sm",
                elem_classes="explanation-btn",
                visible=False
            )
        
        # 隐藏的组件用于复制和下载
        prompts_for_copy = gr.Textbox(visible=False)
        download_file = gr.File(
            label="📁 下载开发计划文档", 
            visible=False,
            interactive=False,
            show_label=True
        )
        
        # 添加复制和下载按钮
        with gr.Row():
            copy_plan_btn = gr.Button(
                "📋 复制开发计划",
                variant="secondary",
                size="sm",
                elem_classes="copy-btn"
            )
            copy_prompts_btn = gr.Button(
                "🤖 复制编程提示词",
                variant="secondary", 
                size="sm",
                elem_classes="copy-btn"
            )
            
        # 下载提示信息
        download_info = gr.HTML(
            value="",
            visible=False,
            elem_id="download_info"
        )
            
        # 使用提示
        gr.HTML("""
        <div style="padding: 10px; background: #e3f2fd; border-radius: 8px; text-align: center; color: #1565c0;" id="usage_tips">
            💡 点击上方按钮复制内容，或下载保存为文件
        </div>
        """)
        
    # 示例区域 - 展示多样化的应用场景
    gr.Markdown("## 🎯 Example Use Cases", elem_id="quick_start_container")
    gr.Examples(
        examples=[
            [
                "AI-powered customer service system: Multi-turn dialogue, sentiment analysis, knowledge base search, automatic ticket generation, and intelligent responses",
                "https://docs.python.org/3/library/asyncio.html"
            ],
            [
                "Modern web application with React and TypeScript: User authentication, real-time data sync, responsive design, PWA support, and offline capabilities",
                "https://react.dev/learn"
            ],
            [
                "Task management platform: Team collaboration, project tracking, deadline reminders, file sharing, and progress visualization",
                ""
            ],
            [
                "E-commerce marketplace: Product catalog, shopping cart, payment integration, order management, and customer reviews",
                "https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps"
            ],
            [
                "Social media analytics dashboard: Data visualization, sentiment analysis, trend tracking, engagement metrics, and automated reporting",
                ""
            ],
            [
                "Educational learning management system: Course creation, student enrollment, progress tracking, assessments, and certificates",
                "https://www.w3.org/WAI/WCAG21/quickref/"
            ]
        ],
        inputs=[idea_input, reference_url_input],
        label="🎯 Popular Examples - Try These Ideas",
        examples_per_page=6,
        elem_id="enhanced_examples"
    )
    
    # 使用说明 - 功能介绍
    gr.HTML("""
    <div class="prompts-section" id="ai_helper_instructions">
        <h3>🚀 How It Works - Intelligent Development Planning</h3>
        
        <!-- 核心功能 -->
        <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #e8f5e8 0%, #f0fff4 100%); border-radius: 15px; border: 3px solid #28a745; margin: 15px 0;">
            <span style="font-size: 36px;">🧠</span><br>
            <strong style="font-size: 18px; color: #155724;">AI-Powered Analysis</strong><br>
            <small style="color: #155724; font-weight: 600; font-size: 13px;">
                � Intelligent planning • ⚡ Fast generation • ✅ Professional output
            </small>
        </div>
        
        <!-- 可视化支持 -->
        <div style="text-align: center; padding: 15px; background: linear-gradient(135deg, #e3f2fd 0%, #f0f8ff 100%); border-radius: 12px; border: 2px solid #2196f3; margin: 15px 0;">
            <span style="font-size: 30px;">�</span><br>
            <strong style="font-size: 16px; color: #1976d2;">Visual Diagrams</strong><br>
            <small style="color: #1976d2; font-weight: 600; font-size: 12px;">
                🎨 Architecture • � Flowcharts • 📅 Gantt charts
            </small>
        </div>
        
        <!-- 处理流程说明 -->
        <div style="background: linear-gradient(135deg, #fff3e0 0%, #fffaf0 100%); padding: 15px; border-radius: 10px; margin: 15px 0; border-left: 4px solid #ff9800;">
            <strong style="color: #f57c00;">⚡ Processing Pipeline:</strong>
            <ol style="margin: 10px 0; padding-left: 20px; font-size: 14px;">
                <li><strong>Input Analysis</strong> → Understanding your requirements</li>
                <li><strong>Prompt Optimization</strong> → Enhancing description quality</li>
                <li><strong>Knowledge Retrieval</strong> → Fetching relevant information</li>
                <li><strong>AI Generation</strong> → Creating comprehensive plan</li>
                <li><strong>Quality Validation</strong> → Ensuring professional output</li>
            </ol>
        </div>
        
        <!-- 核心优势 -->
        <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; margin: 15px 0; border-left: 4px solid #6c757d;">
            <strong style="color: #495057;">🎯 Key Advantages:</strong>
            <ul style="margin: 10px 0; padding-left: 20px; font-size: 14px;">
                <li><strong>Speed</strong> → 60-180 seconds generation time</li>
                <li><strong>Quality</strong> → Professional industry-standard output</li>
                <li><strong>Flexibility</strong> → Multiple export formats</li>
                <li><strong>Integration</strong> → Works with all AI coding assistants</li>
            </ul>
        </div>
        
        <h4>🤖 Perfect for AI Coding Assistants</h4>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; margin: 12px 0;">
            <div style="text-align: center; padding: 8px; background: #e3f2fd; border-radius: 6px; border: 1px solid #2196f3; box-shadow: 0 2px 4px rgba(33,150,243,0.2);">
                <span style="font-size: 16px;">🔵</span> <strong style="font-size: 12px;">Claude</strong>
            </div>
            <div style="text-align: center; padding: 8px; background: #e8f5e8; border-radius: 6px; border: 1px solid #4caf50; box-shadow: 0 2px 4px rgba(76,175,80,0.2);">
                <span style="font-size: 16px;">🟢</span> <strong style="font-size: 12px;">GitHub Copilot</strong>
            </div>
            <div style="text-align: center; padding: 8px; background: #fff3e0; border-radius: 6px; border: 1px solid #ff9800; box-shadow: 0 2px 4px rgba(255,152,0,0.2);">
                <span style="font-size: 16px;">🟡</span> <strong style="font-size: 12px;">ChatGPT</strong>
            </div>
            <div style="text-align: center; padding: 8px; background: #fce4ec; border-radius: 6px; border: 1px solid #e91e63; box-shadow: 0 2px 4px rgba(233,30,99,0.2);">
                <span style="font-size: 16px;">🔴</span> <strong style="font-size: 12px;">Cursor</strong>
            </div>
        </div>
        <p style="text-align: center; color: #28a745; font-weight: 700; font-size: 15px; background: #d4edda; padding: 8px; border-radius: 8px; border: 1px solid #c3e6cb;">
            <em>🎉 Professional Development Plans + Ready-to-Use AI Prompts</em>
        </p>
    </div>
    """)
    
    # 绑定事件
    def show_download_info():
        return gr.update(
            value="""
            <div style="padding: 10px; background: #e8f5e8; border-radius: 8px; text-align: center; margin: 10px 0; color: #2d5a2d;" id="download_success_info">
                ✅ <strong style="color: #1a5a1a;">文档已生成！</strong> 您现在可以：
                <br>• 📋 <span style="color: #2d5a2d;">复制开发计划或编程提示词</span>
                <br>• 📁 <span style="color: #2d5a2d;">点击下方下载按钮保存文档</span>
                <br>• 🔄 <span style="color: #2d5a2d;">调整创意重新生成</span>
            </div>
            """,
            visible=True
        )
    
    # 优化按钮事件
    optimize_btn.click(
        fn=optimize_user_idea,
        inputs=[idea_input],
        outputs=[idea_input, optimization_result]
    ).then(
        fn=lambda: gr.update(visible=True),
        outputs=[optimization_result]
    )
    
    # 重置按钮事件
    reset_btn.click(
        fn=lambda: ("", gr.update(visible=False)),
        outputs=[idea_input, optimization_result]
    )
    
    # 处理过程说明按钮事件
    show_explanation_btn.click(
        fn=show_explanation,
        outputs=[plan_output, process_explanation, hide_explanation_btn]
    )
    
    hide_explanation_btn.click(
        fn=hide_explanation,
        outputs=[plan_output, process_explanation, hide_explanation_btn]
    )
    
    generate_btn.click(
        fn=generate_development_plan,
        inputs=[idea_input, reference_url_input],
        outputs=[plan_output, prompts_for_copy, download_file],
        api_name="generate_plan"
    ).then(
        fn=lambda: gr.update(visible=True),
        outputs=[download_file]
    ).then(
        fn=lambda: gr.update(visible=True),
        outputs=[show_explanation_btn]
    ).then(
        fn=show_download_info,
        outputs=[download_info]
    )
    
    # 复制按钮事件（使用JavaScript实现）
    copy_plan_btn.click(
        fn=None,
        inputs=[plan_output],
        outputs=[],
        js="""(plan_content) => {
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(plan_content).then(() => {
                    alert('✅ 开发计划已复制到剪贴板！');
                }).catch(err => {
                    console.error('复制失败:', err);
                    alert('❌ 复制失败，请手动选择文本复制');
                });
            } else {
                // 降级方案
                const textArea = document.createElement('textarea');
                textArea.value = plan_content;
                document.body.appendChild(textArea);
                textArea.select();
                try {
                    document.execCommand('copy');
                    alert('✅ 开发计划已复制到剪贴板！');
                } catch (err) {
                    alert('❌ 复制失败，请手动选择文本复制');
                }
                document.body.removeChild(textArea);
            }
        }"""
    )
    
    copy_prompts_btn.click(
        fn=None,
        inputs=[prompts_for_copy],
        outputs=[],
        js="""(prompts_content) => {
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(prompts_content).then(() => {
                    alert('✅ 编程提示词已复制到剪贴板！');
                }).catch(err => {
                    console.error('复制失败:', err);
                    alert('❌ 复制失败，请手动选择文本复制');
                });
            } else {
                // 降级方案
                const textArea = document.createElement('textarea');
                textArea.value = prompts_content;
                document.body.appendChild(textArea);
                textArea.select();
                try {
                    document.execCommand('copy');
                    alert('✅ 编程提示词已复制到剪贴板！');
                } catch (err) {
                    alert('❌ 复制失败，请手动选择文本复制');
                }
                document.body.removeChild(textArea);
            }
        }"""
    )

# 启动应用 - 开源版本
if __name__ == "__main__":
    logger.info("🚀 Starting VibeDoc Application")
    logger.info(f"🌍 Environment: {config.environment}")
    logger.info(f"� Version: 2.0.0 - Open Source Edition")
    logger.info(f"�🔧 External Services: {[s.name for s in config.get_enabled_mcp_services()]}")
    
    # 尝试多个端口以避免冲突
    ports_to_try = [7860, 7861, 7862, 7863, 7864]
    launched = False
    
    for port in ports_to_try:
        try:
            logger.info(f"🌐 Attempting to launch on port: {port}")
            demo.launch(
                server_name="0.0.0.0",
                server_port=port,
                share=False,  # 开源版本默认不分享
                show_error=config.debug,
                prevent_thread_lock=False
            )
            launched = True
            logger.info(f"✅ Application successfully launched on port {port}")
            logger.info(f"🔗 Local URL: http://localhost:{port}")
            logger.info(f"🔗 Network URL: http://0.0.0.0:{port}")
            break
        except Exception as e:
            logger.warning(f"⚠️ Port {port} failed: {str(e)}")
            continue
    
    if not launched:
        logger.error("❌ Failed to launch on all ports. Please check network configuration.")
    