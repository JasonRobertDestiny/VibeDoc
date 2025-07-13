import gradio as gr
import requests
import os
import logging
import json
import tempfile
import time
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlparse

# 导入模块化组件
from config import config
from mcp_manager import mcp_manager
from streaming_manager import StreamingGenerator, StreamMessage, StreamMessageType

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
logger.info("🚀 VibeDoc Agent应用启动")
logger.info(f"📊 配置摘要: {json.dumps(config.get_config_summary(), ensure_ascii=False, indent=2)}")

# 验证配置
config_errors = config.validate_config()
if config_errors:
    for key, error in config_errors.items():
        logger.warning(f"⚠️ 配置警告 {key}: {error}")

# 初始化Doubao MCP服务（如果启用）
doubao_service = config.get_mcp_service("doubao")
if doubao_service and doubao_service.enabled:
    logger.info("🎨 初始化Doubao MCP服务...")
    try:
        requests.post(
            doubao_service.url,
            json={"action": "set_api_key", "params": {"api_key": doubao_service.api_key}},
            timeout=10
        )
        logger.info("✅ Doubao API Key设置成功")
    except Exception as e:
        logger.error(f"❌ Doubao API Key设置失败: {e}")

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

def get_mcp_status_display() -> str:
    """获取MCP服务状态显示 - 使用模块化管理器"""
    return mcp_manager.get_status_summary()

def call_mcp_service(url: str, payload: Dict[str, Any], service_name: str, timeout: int = 30) -> Tuple[bool, str]:
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
    try:
        # 简单的HEAD请求检查URL是否存在
        response = requests.head(url, timeout=5, allow_redirects=True)
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
    except Exception as e:
        logger.warning(f"⚠️ URL验证失败: {url} - {str(e)}")
        return f"""
## 🔗 参考链接处理说明

**📍 提供的链接**: {url}

**🔍 处理状态**: 暂时无法验证链接可用性

**🤖 AI处理**: 将基于创意内容进行智能分析，不依赖外部链接

**💡 说明**: 为确保生成质量，AI会根据创意描述生成完整方案，避免引用不确定的外部内容

---
"""
    
    # 尝试调用MCP服务
    success, knowledge = mcp_manager.fetch_knowledge_from_url(url)
    
    if success and knowledge and len(knowledge.strip()) > 50:
        # MCP服务成功返回有效内容
        return knowledge
    else:
        # MCP服务失败或返回无效内容，提供明确说明
        return f"""
## 🔗 外部知识处理说明

**📍 参考链接**: {url}

**🎯 处理方式**: 智能分析模式

**💭 说明**: 当前外部知识服务暂时不可用，AI将基于以下方式生成方案：
- ✅ 基于创意描述进行深度分析
- ✅ 结合行业最佳实践
- ✅ 提供完整的技术方案
- ✅ 生成实用的编程提示词

**🎉 优势**: 确保生成内容的准确性和可靠性，避免引用不确定的外部信息

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

def generate_concept_logo(user_idea: str) -> str:
    """生成概念LOGO和架构图 - 使用模块化配置"""
    doubao_service = config.get_mcp_service("doubao")
    if not doubao_service or not doubao_service.enabled:
        return ""
    
    try:
        logger.info("🎨 使用Doubao MCP生成概念图像...")
        
        # 生成多种类型的图像
        images_generated = []
        
        # 1. 概念LOGO
        logo_prompt = f"Logo design for {user_idea}, minimalist, modern, professional, vector style, clean background, high quality"
        logo_result = generate_image_with_doubao(logo_prompt, "concept-logo", doubao_service)
        if logo_result:
            images_generated.append(("🎨 概念LOGO", logo_result))
        
        # 2. 系统架构图
        arch_prompt = f"System architecture diagram for {user_idea}, technical illustration, components and connections, professional style, clean design"
        arch_result = generate_image_with_doubao(arch_prompt, "architecture", doubao_service)
        if arch_result:
            images_generated.append(("🏗️ 系统架构图", arch_result))
        
        # 3. 用户界面设计图
        ui_prompt = f"User interface mockup for {user_idea}, modern UI design, clean layout, professional appearance"
        ui_result = generate_image_with_doubao(ui_prompt, "ui-design", doubao_service)
        if ui_result:
            images_generated.append(("📱 界面设计图", ui_result))
        
        # 组装所有生成的图像
        if images_generated:
            image_content = "\n\n---\n\n## 🎨 AI生成的概念图像\n\n"
            for title, url in images_generated:
                image_content += f"### {title}\n![{title}]({url})\n\n"
            
            logger.info(f"✅ 成功生成 {len(images_generated)} 个概念图像")
            return image_content
        else:
            logger.warning("⚠️ 未能生成任何概念图像")
            return ""
            
    except Exception as e:
        logger.error(f"💥 概念图像生成错误: {str(e)}")
        return ""

def generate_image_with_doubao(prompt: str, image_type: str, doubao_service) -> str:
    """使用豆包MCP生成单个图像"""
    try:
        # 构建Doubao text_to_image调用的JSON载荷
        image_payload = {
            "action": "text_to_image",
            "params": {
                "prompt": prompt,
                "size": "1024x1024",
                "style": "professional"
            }
        }
        
        # 调用Doubao text_to_image
        image_response = requests.post(
            doubao_service.url,
            json=image_payload,
            timeout=doubao_service.timeout
        )
        
        if image_response.status_code == 200:
            image_data = image_response.json()
            # 解析图像URL（根据实际响应格式调整）
            if "result" in image_data and image_data["result"] and len(image_data["result"]) > 0:
                image_url = image_data["result"][0].get("url", "")
                if image_url:
                    logger.info(f"✅ {image_type} 图像生成成功")
                    return image_url
                else:
                    logger.warning(f"⚠️ {image_type} 响应中未找到图像URL")
            else:
                logger.warning(f"⚠️ {image_type} 图像生成响应格式无效")
        else:
            logger.error(f"❌ {image_type} 图像生成失败: HTTP {image_response.status_code}")
            
    except requests.exceptions.Timeout:
        logger.error(f"⏰ {image_type} 图像生成超时")
    except requests.exceptions.ConnectionError:
        logger.error(f"🔌 {image_type} 图像生成连接失败")
    except Exception as e:
        logger.error(f"💥 {image_type} 图像生成错误: {str(e)}")
    
    return ""

def generate_development_plan_stream(user_idea: str, reference_url: str = ""):
    """
    流式版本：基于用户创意生成完整的产品开发计划
    
    Args:
        user_idea (str): 用户的产品创意描述
        reference_url (str): 可选的参考链接
        
    Yields:
        StreamMessage: 流式消息对象
        
    Returns:
        最终的完整内容
    """
    # 初始化流式生成器
    generator = StreamingGenerator()
    
    try:
        # 🔍 第1阶段：创意验证 (0-10%)
        generator.emit_thought("开始分析您的产品创意，这是一个激动人心的想法！")
        yield generator.emit_progress(10, detail="正在解析创意描述")
        
        # 验证输入
        is_valid, error_msg = validate_input(user_idea)
        if not is_valid:
            yield generator.emit(StreamMessage(
                type=StreamMessageType.ERROR,
                stage=generator.tracker.get_current_stage()['stage'],
                step=1,
                title="创意验证失败",
                progress=0,
                timestamp=datetime.now().isoformat(),
                data={'error': error_msg}
            ))
            return error_msg, "", ""
        
        generator.emit_action("验证API配置和服务状态")
        if not API_KEY:
            error_response = """## ❌ 配置错误：未设置API密钥..."""  # 简化错误信息
            yield generator.emit(StreamMessage(
                type=StreamMessageType.ERROR,
                stage=generator.tracker.get_current_stage()['stage'],
                step=1,
                title="API配置错误",
                progress=0,
                timestamp=datetime.now().isoformat(),
                data={'error': 'API密钥未配置'}
            ))
            return error_response, "", ""
        
        generator.emit_progress(80, detail="创意验证完成 ✅")
        generator.emit_thought("创意验证通过！准备收集外部知识...")
        yield generator.next_stage()
        
        # 📚 第2阶段：知识收集 (10-25%)
        generator.emit_action(f"调用MCP服务获取外部参考资料")
        yield generator.emit_progress(20, detail="连接外部知识库")
        
        # 获取外部知识库内容
        retrieved_knowledge = ""
        if reference_url and reference_url.strip():
            generator.emit_thought(f"发现参考链接：{reference_url[:50]}... 正在深度解析")
            yield generator.emit_progress(40, detail="解析参考链接内容")
            
            retrieved_knowledge = fetch_external_knowledge(reference_url)
            
            if retrieved_knowledge and not any(keyword in retrieved_knowledge for keyword in ["❌", "⚠️"]):
                generator.emit_action("成功获取外部知识，正在整合信息")
                yield generator.emit_progress(80, detail="外部知识获取成功 ✅")
            else:
                generator.emit_thought("外部链接暂时无法访问，将基于创意本身生成方案")
                yield generator.emit_progress(60, detail="使用纯AI模式生成")
        else:
            generator.emit_thought("未提供参考链接，将基于最佳实践生成专业方案")
            yield generator.emit_progress(70, detail="启用AI专家模式")
        
        yield generator.next_stage()
        
        # 🧠 第3阶段：智能分析 (25-45%)
        generator.emit_thought("开始深度分析创意的技术可行性和商业价值...")
        yield generator.emit_progress(10, detail="分析技术栈选型")
        
        # 构建系统提示词和用户提示词  
        # 获取完整的系统提示词（从原函数中获取）
        system_prompt = """你是一个资深技术项目经理，精通产品规划和 AI 编程助手（如 GitHub Copilot、ChatGPT Code）提示词撰写。

🔴 重要要求：
1. 当收到外部知识库参考时，你必须在开发计划中明确引用和融合这些信息
2. 必须在开发计划的开头部分提及参考来源（如CSDN博客、GitHub项目等）
3. 必须根据外部参考调整技术选型和实施建议
4. 必须在相关章节中使用"参考XXX建议"等表述
5. 开发阶段必须有明确编号（第1阶段、第2阶段等）

🚫 严禁行为：
- 绝对不要编造虚假的链接或参考资料
- 不要生成不存在的URL（如 xxx.com、example.com等）
- 不要创建虚假的GitHub仓库链接
- 不要引用不存在的CSDN博客文章

✅ 正确做法：
- 如果没有提供外部参考，直接基于创意进行分析
- 只引用用户实际提供的参考链接
- 当外部知识不可用时，明确说明是基于最佳实践生成

📊 视觉化内容要求（新增）：
- 必须在技术方案中包含架构图的Mermaid代码
- 必须在开发计划中包含甘特图的Mermaid代码
- 必须在功能模块中包含流程图的Mermaid代码
- 必须包含技术栈对比表格
- 必须包含项目里程碑时间表

🎯 必须严格按照Mermaid语法规范生成图表，不能有格式错误

🎯 AI编程提示词格式要求（重要）：
- 必须在开发计划后生成专门的"# AI编程助手提示词"部分
- 每个功能模块必须有一个专门的AI编程提示词
- 每个提示词必须使用```代码块格式，方便复制
- 提示词内容要基于具体项目功能，不要使用通用模板
- 提示词要详细、具体、可直接用于AI编程工具
- 必须包含完整的上下文和具体要求

请严格按照此格式生成个性化的编程提示词，确保每个提示词都基于具体项目需求。

格式要求：先输出开发计划，然后输出编程提示词部分。"""
        
        user_prompt = f"""产品创意：{user_idea}"""
        if retrieved_knowledge and not any(keyword in retrieved_knowledge for keyword in ["❌", "⚠️", "处理说明", "暂时不可用"]):
            user_prompt += f"""

# 外部知识库参考
{retrieved_knowledge}

请基于上述外部知识库参考和产品创意生成："""
            generator.emit_action("结合外部知识库优化技术方案")
        else:
            user_prompt += """

请生成："""
        
        user_prompt += """
1. 详细的开发计划（包含产品概述、技术方案、开发计划、部署方案、推广策略等）
2. 每个功能模块对应的AI编程助手提示词

确保提示词具体、可操作，能直接用于AI编程工具。"""
        
        yield generator.emit_progress(60, detail="构建AI生成策略")
        generator.emit_thought("AI分析完成，准备生成完整方案...")
        yield generator.emit_progress(90, detail="智能分析完成 ✅")
        yield generator.next_stage()
        
        # ⚡ 第4阶段：方案生成 (45-75%)
        generator.emit_action("调用Qwen2.5-72B-Instruct大模型")
        yield generator.emit_progress(10, detail="连接AI服务")
        
        generator.emit_thought("正在与AI大模型进行深度对话，生成您的专属方案...")
        yield generator.emit_progress(30, detail="AI思考中...")
        
        # 调用AI API
        response = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "Qwen/Qwen2.5-72B-Instruct",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 4000,
                "temperature": 0.7
            },
            timeout=120
        )
        
        yield generator.emit_progress(60, detail="AI生成中...")
        
        if response.status_code == 200:
            content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                generator.emit_action("AI方案生成成功，准备内容处理")
                yield generator.emit_progress(90, detail="方案生成完成 ✅")
                yield generator.next_stage()
                
                # ✨ 第5阶段：内容美化 (75-90%)
                generator.emit_thought("开始美化内容格式，生成图表和优化排版...")
                yield generator.emit_progress(20, detail="格式化文档结构")
                
                # 后处理：确保内容结构化
                final_plan_text = format_response(content)
                yield generator.emit_progress(50, detail="生成Mermaid图表")
                
                # 分段推送内容
                sections = final_plan_text.split('\n## ')
                for i, section in enumerate(sections[:3]):  # 推送前3个主要部分
                    if section.strip():
                        section_title = section.split('\n')[0].replace('#', '').strip()
                        yield generator.emit_content(
                            content=f"## {section}" if i > 0 else section,
                            section=section_title,
                            section_index=i
                        )
                
                # 生成概念LOGO图像
                generator.emit_action("生成概念设计图像")
                yield generator.emit_progress(80, detail="创建概念图像")
                
                logo_content = generate_concept_logo(user_idea)
                if logo_content:
                    final_plan_text += logo_content
                    yield generator.emit_content(
                        content=logo_content,
                        section="concept_logo",
                        section_index=99
                    )
                
                yield generator.emit_progress(95, detail="内容美化完成 ✅")
                yield generator.next_stage()
                
                # 🎯 第6阶段：最终输出 (90-100%)
                generator.emit_action("创建下载文件")
                yield generator.emit_progress(30, detail="生成Markdown文件")
                
                # 创建临时文件
                temp_file = create_temp_markdown_file(final_plan_text)
                
                generator.emit_action("提取AI编程提示词")
                yield generator.emit_progress(70, detail="生成编程助手提示词")
                
                prompts_section = extract_prompts_section(final_plan_text)
                
                # 推送最终的提示词部分
                yield generator.emit_content(
                    content=prompts_section,
                    section="ai_prompts",
                    section_index=100
                )
                
                yield generator.emit_progress(100, detail="所有内容生成完成 🎉")
                yield generator.next_stage()  # 发送FINAL消息
                
                return final_plan_text, prompts_section, temp_file
            else:
                error_msg = "❌ AI返回空内容"
                yield generator.emit(StreamMessage(
                    type=StreamMessageType.ERROR,
                    stage=generator.tracker.get_current_stage()['stage'],
                    step=4,
                    title="内容生成失败",
                    progress=0,
                    timestamp=datetime.now().isoformat(),
                    data={'error': error_msg}
                ))
                return error_msg, "", ""
        else:
            error_msg = f"❌ API请求失败: HTTP {response.status_code}"
            yield generator.emit(StreamMessage(
                type=StreamMessageType.ERROR,
                stage=generator.tracker.get_current_stage()['stage'],
                step=4,
                title="API调用失败",
                progress=0,
                timestamp=datetime.now().isoformat(),
                data={'error': error_msg, 'status_code': response.status_code}
            ))
            return error_msg, "", ""
            
    except requests.exceptions.Timeout:
        error_msg = "❌ API请求超时，请稍后重试"
        yield generator.emit(StreamMessage(
            type=StreamMessageType.ERROR,
            stage=generator.tracker.get_current_stage()['stage'],
            step=generator.tracker.get_current_stage()['step'],
            title="请求超时",
            progress=0,
            timestamp=datetime.now().isoformat(),
            data={'error': error_msg}
        ))
        return error_msg, "", ""
    except requests.exceptions.ConnectionError:
        error_msg = "❌ 网络连接失败，请检查网络设置"
        yield generator.emit(StreamMessage(
            type=StreamMessageType.ERROR,
            stage=generator.tracker.get_current_stage()['stage'],
            step=generator.tracker.get_current_stage()['step'],
            title="网络连接失败",
            progress=0,
            timestamp=datetime.now().isoformat(),
            data={'error': error_msg}
        ))
        return error_msg, "", ""
    except Exception as e:
        error_msg = f"❌ 处理错误: {str(e)}"
        yield generator.emit(StreamMessage(
            type=StreamMessageType.ERROR,
            stage=generator.tracker.get_current_stage()['stage'],
            step=generator.tracker.get_current_stage()['step'],
            title="系统错误",
            progress=0,
            timestamp=datetime.now().isoformat(),
            data={'error': error_msg, 'exception': str(e)}
        ))
        return error_msg, "", ""


def generate_development_plan(user_idea: str, reference_url: str = "") -> Tuple[str, str, str]:
    """
    基于用户创意生成完整的产品开发计划和对应的AI编程助手提示词。
    
    Args:
        user_idea (str): 用户的产品创意描述
        reference_url (str): 可选的参考链接
        
    Returns:
        Tuple[str, str, str]: 开发计划、AI编程提示词、临时文件路径
    """
    # 验证输入
    is_valid, error_msg = validate_input(user_idea)
    if not is_valid:
        return error_msg, "", ""
        
    if not API_KEY:
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
        return error_msg, "", ""
    
    # 获取外部知识库内容
    retrieved_knowledge = fetch_external_knowledge(reference_url)
    
    # 构建系统提示词 - 防止虚假链接生成，强化编程提示词生成，增强视觉化内容
    system_prompt = """你是一个资深技术项目经理，精通产品规划和 AI 编程助手（如 GitHub Copilot、ChatGPT Code）提示词撰写。

🔴 重要要求：
1. 当收到外部知识库参考时，你必须在开发计划中明确引用和融合这些信息
2. 必须在开发计划的开头部分提及参考来源（如CSDN博客、GitHub项目等）
3. 必须根据外部参考调整技术选型和实施建议
4. 必须在相关章节中使用"参考XXX建议"等表述
5. 开发阶段必须有明确编号（第1阶段、第2阶段等）

🚫 严禁行为：
- 绝对不要编造虚假的链接或参考资料
- 不要生成不存在的URL（如 xxx.com、example.com等）
- 不要创建虚假的GitHub仓库链接
- 不要引用不存在的CSDN博客文章

✅ 正确做法：
- 如果没有提供外部参考，直接基于创意进行分析
- 只引用用户实际提供的参考链接
- 当外部知识不可用时，明确说明是基于最佳实践生成

📊 视觉化内容要求（新增）：
- 必须在技术方案中包含架构图的Mermaid代码
- 必须在开发计划中包含甘特图的Mermaid代码
- 必须在功能模块中包含流程图的Mermaid代码
- 必须包含技术栈对比表格
- 必须包含项目里程碑时间表

🎯 Mermaid图表格式要求（v11.4.1兼容版）：

**流程图示例：**
```mermaid
flowchart TD
    A[项目启动] --> B{需求明确?}
    B -->|是| C[技术选型]
    B -->|否| D[需求调研]
    D --> B
    C --> E[系统设计]
    E --> F[开发实施]
    F --> G[测试验证]
    G --> H[部署上线]
    
    style A fill:#e1f5fe
    style H fill:#c8e6c9
    style B fill:#fff3e0
```

**架构图示例：**
```mermaid
graph TB
    subgraph "前端层"
        UI[用户界面]
        APP[移动应用]
    end
    
    subgraph "业务层"
        API[API网关]
        AUTH[认证服务]
        BIZ[业务服务]
    end
    
    subgraph "数据层"
        DB[(数据库)]
        CACHE[(缓存)]
        FILE[(文件存储)]
    end
    
    UI --> API
    APP --> API
    API --> AUTH
    API --> BIZ
    BIZ --> DB
    BIZ --> CACHE
    BIZ --> FILE
```

🎯 甘特图格式要求（Mermaid v11.4.1优化版）：
```mermaid
gantt
    title 项目开发计划甘特图
    dateFormat YYYY-MM-DD
    axisFormat %m/%d
    
    section 第一阶段：需求分析
        需求调研         :active, req1, 2025-01-01, 3d
        需求整理         :req2, after req1, 2d
        需求评审         :milestone, req3, after req2, 1d
    
    section 第二阶段：系统设计
        架构设计         :design1, after req3, 5d
        详细设计         :design2, after design1, 4d
        设计评审         :milestone, design3, after design2, 1d
    
    section 第三阶段：开发实施
        前端开发         :dev1, after design3, 10d
        后端开发         :dev2, after design3, 12d
        接口联调         :dev3, after dev1 dev2, 3d
    
    section 第四阶段：测试部署
        系统测试         :test1, after dev3, 5d
        用户验收         :test2, after test1, 3d
        生产部署         :milestone, deploy, after test2, 1d
```

🎯 甘特图语法注意事项：
- 使用 `active` 标记当前进行的任务
- 使用 `milestone` 标记重要里程碑  
- 使用 `after` 关键字定义任务依赖关系
- 日期格式严格遵循 YYYY-MM-DD
- 任务名称避免使用特殊字符

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
        logger.info("Calling AI API for development plan generation...")
        
        response = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "Qwen/Qwen2.5-72B-Instruct",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 4000,
                "temperature": 0.7
            },
            timeout=120
        )
        
        if response.status_code == 200:
            content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                # 后处理：确保内容结构化
                final_plan_text = format_response(content)
                
                # 生成概念LOGO图像
                logo_content = generate_concept_logo(user_idea)
                if logo_content:
                    final_plan_text += logo_content
                
                # 创建临时文件
                temp_file = create_temp_markdown_file(final_plan_text)
                
                return final_plan_text, extract_prompts_section(final_plan_text), temp_file
            else:
                logger.error("API returned empty content")
                return "❌ API返回空内容", "", ""
        else:
            logger.error(f"API request failed with status {response.status_code}")
            return f"❌ API请求失败: HTTP {response.status_code}", "", ""
            
    except requests.exceptions.Timeout:
        logger.error("API request timeout")
        return "❌ API请求超时，请稍后重试", "", ""
    except requests.exceptions.ConnectionError:
        logger.error("API connection failed")
        return "❌ 网络连接失败，请检查网络设置", "", ""
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return f"❌ 处理错误: {str(e)}", "", ""

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
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8')
        temp_file.write(content)
        temp_file.close()
        logger.info(f"Created temporary file: {temp_file.name}")
        return temp_file.name
    except Exception as e:
        logger.error(f"Failed to create temporary file: {e}")
        return ""

def format_response(content: str) -> str:
    """格式化AI回复，美化显示并保持原始AI生成的提示词"""
    
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
    """美化AI编程提示词显示，为每个提示词添加复制按钮"""
    lines = prompts_content.split('\n')
    enhanced_lines = []
    in_code_block = False
    current_prompt_id = 0
    current_prompt_content = ""
    
    for line in lines:
        stripped = line.strip()
        
        # 处理标题
        if stripped.startswith('# AI编程助手提示词'):
            enhanced_lines.append('')
            enhanced_lines.append('<div class="prompts-highlight">')
            enhanced_lines.append('')
            enhanced_lines.append('# 🤖 AI编程助手提示词')
            enhanced_lines.append('')
            enhanced_lines.append('> 💡 **使用说明**：以下提示词基于您的项目需求定制生成，可直接复制到 Claude Code、GitHub Copilot、ChatGPT 等AI编程工具中使用')
            enhanced_lines.append('')
            continue
            
        # 处理二级标题（功能模块）
        if stripped.startswith('## ') and not in_code_block:
            title = stripped[3:].strip()
            current_prompt_id += 1
            enhanced_lines.append('')
            enhanced_lines.append('<div class="prompt-section">')
            enhanced_lines.append('')
            enhanced_lines.append(f'## 🎯 {title}')
            enhanced_lines.append('')
            continue
            
        # 处理代码块开始
        if stripped.startswith('```') and not in_code_block:
            in_code_block = True
            current_prompt_content = ""  # 开始收集提示词内容
            enhanced_lines.append('')
            enhanced_lines.append('<div class="prompt-code-block">')
            enhanced_lines.append('')
            enhanced_lines.append('```prompt')
            continue
            
        # 处理代码块内容
        if in_code_block and not stripped.startswith('```'):
            current_prompt_content += line + '\n'
            enhanced_lines.append(line)
            continue
            
        # 处理代码块结束
        if stripped.startswith('```') and in_code_block:
            in_code_block = False
            # 添加复制按钮
            clean_prompt = current_prompt_content.strip()
            # 安全地编码内容，避免JavaScript注入
            import html
            encoded_prompt = html.escape(clean_prompt).replace('\n', '\\n').replace("'", "\\'")
            
            enhanced_lines.append('```')
            enhanced_lines.append('')
            enhanced_lines.append('<div class="prompt-copy-section">')
            enhanced_lines.append(f'<button class="individual-copy-btn" data-prompt-id="{current_prompt_id}" data-prompt-content="{encoded_prompt}">')
            enhanced_lines.append('    📋 复制此提示词')
            enhanced_lines.append('</button>')
            enhanced_lines.append('<span class="copy-success-msg" id="copy-success-' + str(current_prompt_id) + '" style="display: none; color: #28a745; margin-left: 10px;">✅ 已复制!</span>')
            enhanced_lines.append('</div>')
            enhanced_lines.append('')
            enhanced_lines.append('</div>')
            enhanced_lines.append('')
            enhanced_lines.append('</div>')
            enhanced_lines.append('')
            current_prompt_content = ""
            continue
            
        # 其他内容保持原样
        enhanced_lines.append(line)
    
    # 如果还在代码块中，需要关闭
    if in_code_block:
        enhanced_lines.extend(['```', '', '</div>', '', '</div>'])
    
    # 关闭主容器
    enhanced_lines.extend(['', '</div>', ''])
    
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
            phase_num = stripped.split('第')[1].split('阶段')[0] if '第' in stripped else ''
            phase_name = stripped.split('：')[1] if '：' in stripped else stripped
            enhanced_lines.append(f"\n#### 🚀 第{phase_num}阶段：{phase_name}\n")
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

/* 重构后的单栏居中创作画布 */
.main-creation-canvas {
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border-radius: 2rem;
    box-shadow: 0 12px 40px rgba(59, 130, 246, 0.15);
    border: 1px solid #e2e8f0;
}

.content-card {
    background: transparent;
    padding: 0;
    border-radius: 0;
    box-shadow: none;
    margin: 0;
    border: none;
}

.dark .content-card {
    background: transparent;
    border-color: transparent;
}

.dark .main-creation-canvas {
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
    margin: 1rem 0;
    padding: 0.5rem;
    background: rgba(66, 153, 225, 0.05);
    border-radius: 0.5rem;
}

.individual-copy-btn {
    background: linear-gradient(45deg, #4299e1, #3182ce) !important;
    border: none !important;
    color: white !important;
    padding: 0.6rem 1.2rem !important;
    border-radius: 1.5rem !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 2px 8px rgba(66, 153, 225, 0.3) !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 0.5rem !important;
}

.individual-copy-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 15px rgba(66, 153, 225, 0.4) !important;
    background: linear-gradient(45deg, #3182ce, #2c5aa0) !important;
}

.individual-copy-btn:active {
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
}

.dark .individual-copy-btn:hover {
    background: linear-gradient(45deg, #4299e1, #3182ce) !important;
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

/* Enhanced Loading & Progress System */
.progress-container {
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    border-radius: 1.5rem;
    padding: 2rem;
    text-align: center;
    border: 2px solid #0ea5e9;
    margin: 2rem 0;
    position: relative;
    overflow: hidden;
}

.progress-container::before {
    content: "";
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 4px;
    background: linear-gradient(90deg, #0ea5e9, #3b82f6, #6366f1);
    animation: progressWave 3s ease-in-out infinite;
}

@keyframes progressWave {
    0% { left: -100%; }
    50% { left: 0%; }
    100% { left: 100%; }
}

.progress-steps {
    display: flex;
    justify-content: space-between;
    margin: 1.5rem 0;
    flex-wrap: wrap;
    gap: 1rem;
}

.progress-step {
    flex: 1;
    min-width: 120px;
    padding: 0.8rem;
    border-radius: 1rem;
    background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
    border: 2px solid #cbd5e0;
    transition: all 0.5s ease;
    position: relative;
}

.progress-step.active {
    background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
    border-color: #3b82f6;
    transform: scale(1.05);
}

.progress-step.completed {
    background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
    border-color: #10b981;
}

.progress-step .step-icon {
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
    display: block;
}

.progress-step .step-text {
    font-weight: 600;
    color: #374151;
    font-size: 0.9rem;
}

.progress-step.active .step-text {
    color: #1d4ed8;
}

.progress-step.completed .step-text {
    color: #059669;
}

.progress-spinner {
    display: inline-block;
    width: 3rem;
    height: 3rem;
    border: 4px solid #e5e7eb;
    border-top: 4px solid #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 1rem 0;
}

.progress-time {
    color: #6b7280;
    font-size: 0.9rem;
    margin-top: 1rem;
    font-style: italic;
}

/* Dark theme support */
.dark .progress-container {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-color: #3b82f6;
}

.dark .progress-step {
    background: linear-gradient(135deg, #374151 0%, #1f2937 100%);
    border-color: #4b5563;
}

.dark .progress-step.active {
    background: linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%);
    border-color: #60a5fa;
}

.dark .progress-step .step-text {
    color: #f3f4f6;
}

/* 流式进度跟踪器样式 */
.streaming-tracker-container {
    padding: 1rem;
}

.tracker-container {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    border-radius: 1.5rem;
    padding: 1.5rem;
    border: 2px solid #e2e8f0;
    margin-bottom: 1rem;
    transition: all 0.3s ease;
}

.tracker-title {
    color: #1e40af;
    margin-bottom: 1.5rem;
    font-weight: 700;
    text-align: center;
    font-size: 1.2rem;
}

/* 整体进度条 */
.overall-progress {
    margin-bottom: 2rem;
}

.progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}

.progress-text {
    font-weight: 600;
    color: #374151;
}

.progress-percentage {
    font-weight: 700;
    color: #1e40af;
    font-size: 1.1rem;
}

.progress-bar-container {
    height: 12px;
    background: #e5e7eb;
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 0.5rem;
}

.progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #3b82f6, #1d4ed8, #7c3aed);
    width: 0%;
    border-radius: 6px;
    transition: width 0.8s ease;
    position: relative;
}

.progress-bar::after {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(45deg, transparent 40%, rgba(255,255,255,0.3) 50%, transparent 60%);
    animation: progressShine 2s infinite;
}

@keyframes progressShine {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

.progress-eta {
    font-size: 0.9rem;
    color: #6b7280;
    text-align: center;
}

/* 步骤清单 */
.steps-checklist {
    space-y: 0.75rem;
}

.step-item {
    display: flex;
    align-items: center;
    padding: 1rem;
    background: rgba(255, 255, 255, 0.7);
    border-radius: 1rem;
    border: 2px solid #e5e7eb;
    transition: all 0.3s ease;
    margin-bottom: 0.75rem;
    position: relative;
}

.step-item.waiting {
    border-color: #e5e7eb;
    opacity: 0.7;
}

.step-item.active {
    border-color: #3b82f6;
    background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
    transform: scale(1.02);
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    animation: stepPulse 2s infinite;
}

.step-item.completed {
    border-color: #10b981;
    background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
}

.step-item.error {
    border-color: #ef4444;
    background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
}

@keyframes stepPulse {
    0%, 100% { box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3); }
    50% { box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5); }
}

.step-icon {
    font-size: 1.5rem;
    margin-right: 1rem;
    flex-shrink: 0;
}

.step-content {
    flex-grow: 1;
}

.step-title {
    font-weight: 600;
    color: #1f2937;
    margin-bottom: 0.25rem;
}

.step-description {
    font-size: 0.85rem;
    color: #6b7280;
    margin-bottom: 0.25rem;
}

.step-status {
    font-size: 0.8rem;
    font-weight: 500;
    color: #9ca3af;
}

.step-item.active .step-status {
    color: #1d4ed8;
    font-weight: 600;
}

.step-item.completed .step-status {
    color: #059669;
    font-weight: 600;
}

.step-item.completed .step-status::after {
    content: " ✓";
}

.step-progress-mini {
    width: 4px;
    height: 40px;
    background: #e5e7eb;
    border-radius: 2px;
    margin-left: 1rem;
    position: relative;
    overflow: hidden;
}

.step-item.active .step-progress-mini::after {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 0%;
    background: linear-gradient(180deg, #3b82f6, #1d4ed8);
    border-radius: 2px;
    animation: miniProgress 3s ease-in-out infinite;
}

@keyframes miniProgress {
    0%, 100% { height: 0%; }
    50% { height: 100%; }
}

/* 当前活动显示 */
.current-activity {
    background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
    border-radius: 1rem;
    padding: 1rem;
    border: 2px solid #93c5fd;
}

.activity-header {
    display: flex;
    align-items: center;
    margin-bottom: 0.5rem;
}

.activity-icon {
    font-size: 1.2rem;
    margin-right: 0.5rem;
}

.activity-title {
    font-weight: 600;
    color: #1e40af;
}

.activity-content {
    color: #374151;
    font-size: 0.9rem;
    line-height: 1.4;
}

/* AI思考过程窗口 */
.thought-container {
    max-height: 300px;
    overflow: hidden;
    border-radius: 1rem;
    border: 2px solid #e5e7eb;
}

.thought-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
    border-bottom: 1px solid #d1d5db;
}

.thought-icon {
    margin-right: 0.5rem;
}

.thought-title {
    font-weight: 600;
    color: #374151;
}

.clear-log-btn {
    background: #6b7280;
    color: white;
    border: none;
    padding: 0.25rem 0.5rem;
    border-radius: 0.375rem;
    font-size: 0.75rem;
    cursor: pointer;
    transition: background 0.2s;
}

.clear-log-btn:hover {
    background: #4b5563;
}

.thought-log {
    max-height: 240px;
    overflow-y: auto;
    padding: 1rem;
    background: #ffffff;
}

.thought-entry {
    margin-bottom: 0.75rem;
    padding: 0.5rem;
    border-radius: 0.5rem;
    background: #f9fafb;
    border-left: 3px solid #d1d5db;
    animation: thoughtAppear 0.3s ease-out;
}

.thought-entry.thought {
    border-left-color: #8b5cf6;
    background: #faf5ff;
}

.thought-entry.action {
    border-left-color: #f59e0b;
    background: #fffbeb;
}

.thought-entry.error {
    border-left-color: #ef4444;
    background: #fef2f2;
}

@keyframes thoughtAppear {
    from {
        opacity: 0;
        transform: translateY(-10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.thought-time {
    font-size: 0.7rem;
    color: #9ca3af;
    margin-right: 0.5rem;
}

.thought-text {
    color: #374151;
    font-size: 0.85rem;
}

/* 暗色主题适配 */
.dark .tracker-container {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-color: #374151;
}

.dark .step-item {
    background: rgba(55, 65, 81, 0.7);
    border-color: #4b5563;
}

.dark .step-item.active {
    background: linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%);
    border-color: #60a5fa;
}

.dark .step-title {
    color: #f3f4f6;
}

.dark .thought-container {
    border-color: #4b5563;
}

.dark .thought-log {
    background: #1f2937;
}

.dark .thought-entry {
    background: #374151;
    border-left-color: #6b7280;
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
"""

# 保持美化的Gradio界面
with gr.Blocks(
    title="VibeDoc Agent：您的随身AI产品经理与架构师",
    theme=gr.themes.Soft(primary_hue="blue"),
    css=custom_css
) as demo:
    
    gr.HTML("""
    <div class="header-gradient">
        <h1>🚀 VibeDoc Agent：您的随身AI产品经理与架构师</h1>
        <p style="font-size: 18px; margin: 15px 0; opacity: 0.95;">
            基于AI的Agent应用，集成多种MCP服务提供智能开发计划生成
        </p>
        <p style="opacity: 0.85;">
            一键将创意转化为完整的开发方案 + AI编程助手提示词，展示Agent应用与MCP服务协作能力
        </p>
    </div>
    
    <!-- 升级Mermaid.js至v11.4.1最新稳定版 -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"></script>
    <script>
        // Mermaid v11.4.1 增强配置 - 专门优化甘特图显示
        mermaid.initialize({ 
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose', // 提高兼容性
            maxTextSize: 90000,     // 增加文本限制
            flowchart: {
                useMaxWidth: true,
                htmlLabels: true,
                curve: 'linear'
            },
            gantt: {
                displayMode: 'standard',     // 甘特图显示模式
                leftPadding: 75,            // 左侧填充
                gridLineStartPadding: 35,   // 网格线起始填充
                fontSize: 11,               // 字体大小
                fontFamily: '"Open Sans", sans-serif',
                sectionFontSize: 24,        // 节标题字体大小
                numberSectionStyles: 4,     // 节样式数量
                useWidth: 1200,             // 固定宽度，避免渲染问题
                useMaxWidth: true
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
                tertiaryBkg: '#eff6ff',
                // 甘特图专用变量
                cScale0: '#3b82f6',
                cScale1: '#60a5fa', 
                cScale2: '#93c5fd',
                section0: '#1e40af',
                section1: '#2563eb',
                section2: '#3b82f6',
                section3: '#60a5fa'
            }
        });
        
        // 监听主题变化，动态更新Mermaid主题
        function updateMermaidTheme() {
            const isDark = document.documentElement.classList.contains('dark');
            const theme = isDark ? 'dark' : 'default';
            mermaid.initialize({ 
                startOnLoad: true,
                theme: theme,
                securityLevel: 'loose',
                maxTextSize: 90000,
                flowchart: {
                    useMaxWidth: true,
                    htmlLabels: true,
                    curve: 'linear'
                },
                gantt: {
                    displayMode: 'standard',
                    leftPadding: 75,
                    gridLineStartPadding: 35,
                    fontSize: 11,
                    fontFamily: '"Open Sans", sans-serif',
                    sectionFontSize: 24,
                    numberSectionStyles: 4,
                    useWidth: 1200,
                    useMaxWidth: true
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
                    tertiaryBkg: '#1e293b',
                    // 暗色主题甘特图专用变量
                    cScale0: '#60a5fa',
                    cScale1: '#3b82f6',
                    cScale2: '#2563eb',
                    section0: '#60a5fa',
                    section1: '#3b82f6',
                    section2: '#2563eb',
                    section3: '#1d4ed8'
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
                    tertiaryBkg: '#eff6ff',
                    // 亮色主题甘特图专用变量
                    cScale0: '#3b82f6',
                    cScale1: '#60a5fa',
                    cScale2: '#93c5fd',
                    section0: '#1e40af',
                    section1: '#2563eb',
                    section2: '#3b82f6',
                    section3: '#60a5fa'
                }
            });
        }
        
        // 甘特图语法验证和修复函数
        function validateAndFixGanttChart(code) {
            // 基本语法检查和修复
            let fixedCode = code.trim();
            
            // 确保以 gantt 开头
            if (!fixedCode.startsWith('gantt')) {
                console.warn('⚠️ 甘特图缺少 gantt 声明');
                return null;
            }
            
            // 检查必需的格式声明
            if (!fixedCode.includes('dateFormat')) {
                fixedCode = fixedCode.replace('gantt', 'gantt\n    dateFormat YYYY-MM-DD');
                console.log('🔧 自动添加 dateFormat 声明');
            }
            
            // 修复常见的语法问题
            fixedCode = fixedCode
                // 修复缺少冒号的任务定义
                .replace(/^(\\s+)([^:\\n]+)(\\s+)([a-zA-Z0-9_]+,)/gm, '$1$2 :$4')
                // 修复日期格式问题
                .replace(/(\\d{4})-(\\d{1})-(\\d{1})/g, '$1-0$2-0$3')
                .replace(/(\\d{4})-(\\d{2})-(\\d{1})/g, '$1-$2-0$3')
                .replace(/(\\d{4})-(\\d{1})-(\\d{2})/g, '$1-0$2-$3')
                // 移除可能导致问题的特殊字符
                .replace(/[""'']/g, '"')
                .replace(/[，]/g, ',');
            
            // 验证基本结构
            const lines = fixedCode.split('\n');
            let hasTitle = false;
            let hasSection = false;
            let hasTask = false;
            
            for (const line of lines) {
                const trimmedLine = line.trim();
                if (trimmedLine.startsWith('title')) hasTitle = true;
                if (trimmedLine.startsWith('section')) hasSection = true;
                if (trimmedLine.includes(':') && !trimmedLine.startsWith('title') && 
                    !trimmedLine.startsWith('dateFormat') && !trimmedLine.startsWith('axisFormat')) {
                    hasTask = true;
                }
            }
            
            if (!hasSection || !hasTask) {
                console.error('❌ 甘特图结构不完整：缺少section或task');
                return null;
            }
            
            console.log('✅ 甘特图语法验证通过');
            return fixedCode;
        }
        
        // 流式数据处理器 - 处理AI工作实况
        class StreamProcessor {
            constructor() {
                this.tracker = null;
                this.thoughtLog = null;
                this.isActive = false;
                this.thoughtCount = 0;
            }
            
            initialize() {
                this.tracker = document.getElementById('generation-status-tracker');
                this.thoughtLog = document.getElementById('thought-log');
                console.log('🔥 StreamProcessor initialized');
            }
            
            startStreaming() {
                if (!this.tracker) this.initialize();
                
                this.isActive = true;
                this.thoughtCount = 0;
                
                // 显示进度跟踪器
                if (this.tracker) {
                    this.tracker.style.display = 'block';
                }
                
                // 重置所有步骤状态
                this.resetAllSteps();
                
                // 添加开始日志
                this.addThoughtEntry('开始AI生成流程...', 'action');
                
                console.log('🚀 Stream started');
            }
            
            processMessage(data) {
                if (!this.isActive) return;
                
                try {
                    console.log('📨 Processing stream message:', data);
                    
                    const message = typeof data === 'string' ? JSON.parse(data) : data;
                    
                    switch (message.type) {
                        case 'progress':
                            this.updateProgress(message);
                            break;
                        case 'thought':
                            this.addThought(message);
                            break;
                        case 'action':
                            this.addAction(message);
                            break;
                        case 'content':
                            this.addContent(message);
                            break;
                        case 'complete':
                            this.completeStep(message);
                            break;
                        case 'error':
                            this.showError(message);
                            break;
                        case 'final':
                            this.finishStreaming(message);
                            break;
                    }
                } catch (error) {
                    console.error('❌ Stream processing error:', error);
                }
            }
            
            updateProgress(message) {
                // 更新整体进度条
                const progressBar = document.getElementById('overall-progress-bar');
                const progressText = document.querySelector('.progress-percentage');
                const etaElement = document.getElementById('eta-time');
                
                if (progressBar) {
                    progressBar.style.width = `${message.progress}%`;
                }
                
                if (progressText) {
                    progressText.textContent = `${Math.round(message.progress)}%`;
                }
                
                // 更新预计完成时间
                if (etaElement && message.data.estimated_remaining) {
                    const minutes = Math.floor(message.data.estimated_remaining / 60);
                    const seconds = message.data.estimated_remaining % 60;
                    etaElement.textContent = minutes > 0 ? 
                        `${minutes}分${seconds}秒` : 
                        `${seconds}秒`;
                }
                
                // 更新步骤状态
                this.updateStepStatus(message.step, 'active', message.title);
                
                // 更新当前活动
                this.updateCurrentActivity(message.title, message.data.detail || '');
            }
            
            updateStepStatus(step, status, title) {
                const stepElement = document.querySelector(`[data-step="${step}"]`);
                if (!stepElement) return;
                
                // 清除之前的状态
                stepElement.classList.remove('waiting', 'active', 'completed', 'error');
                
                // 添加新状态
                stepElement.classList.add(status);
                
                // 更新状态文本
                const statusElement = stepElement.querySelector('.step-status');
                if (statusElement) {
                    switch (status) {
                        case 'active':
                            statusElement.textContent = '进行中...';
                            break;
                        case 'completed':
                            statusElement.textContent = '已完成';
                            break;
                        case 'error':
                            statusElement.textContent = '出错了';
                            break;
                        default:
                            statusElement.textContent = '等待中';
                    }
                }
            }
            
            addThought(message) {
                this.addThoughtEntry(message.data.thought, 'thought');
            }
            
            addAction(message) {
                this.addThoughtEntry(`🔧 ${message.data.action}`, 'action');
                this.updateCurrentActivity('执行中', message.data.action);
            }
            
            addContent(message) {
                this.addThoughtEntry(`📄 生成了${message.data.section}内容`, 'action');
                
                // 这里可以添加渐进式内容渲染
                // TODO: 实现渐进式内容显示
            }
            
            completeStep(message) {
                this.updateStepStatus(message.step, 'completed', message.title);
                this.addThoughtEntry(`✅ ${message.title} 完成`, 'action');
            }
            
            showError(message) {
                this.updateStepStatus(message.step, 'error', message.title);
                this.addThoughtEntry(`❌ 错误: ${message.data.error}`, 'error');
                this.updateCurrentActivity('出现错误', message.data.error);
            }
            
            finishStreaming(message) {
                this.isActive = false;
                
                // 标记所有步骤为完成
                for (let i = 1; i <= 6; i++) {
                    this.updateStepStatus(i, 'completed', '');
                }
                
                // 更新进度条到100%
                const progressBar = document.getElementById('overall-progress-bar');
                const progressText = document.querySelector('.progress-percentage');
                
                if (progressBar) progressBar.style.width = '100%';
                if (progressText) progressText.textContent = '100%';
                
                this.updateCurrentActivity('🎉 生成完成', '您的开发方案已经准备就绪！');
                this.addThoughtEntry('🎉 所有内容生成完成！', 'action');
                
                console.log('✅ Stream finished');
            }
            
            resetAllSteps() {
                for (let i = 1; i <= 6; i++) {
                    this.updateStepStatus(i, 'waiting', '');
                }
                
                // 重置进度条
                const progressBar = document.getElementById('overall-progress-bar');
                const progressText = document.querySelector('.progress-percentage');
                
                if (progressBar) progressBar.style.width = '0%';
                if (progressText) progressText.textContent = '0%';
            }
            
            updateCurrentActivity(title, detail) {
                const activityElement = document.getElementById('current-activity-text');
                if (activityElement) {
                    activityElement.innerHTML = `
                        <strong>${title}</strong>
                        ${detail ? `<br><span style="opacity: 0.8;">${detail}</span>` : ''}
                    `;
                }
            }
            
            addThoughtEntry(text, type = 'thought') {
                if (!this.thoughtLog) return;
                
                this.thoughtCount++;
                const now = new Date();
                const timeStr = now.toLocaleTimeString('zh-CN', { 
                    hour12: false, 
                    hour: '2-digit', 
                    minute: '2-digit', 
                    second: '2-digit' 
                });
                
                const entry = document.createElement('div');
                entry.className = `thought-entry ${type}`;
                entry.innerHTML = `
                    <span class="thought-time">${timeStr}</span>
                    <span class="thought-text">${text}</span>
                `;
                
                this.thoughtLog.appendChild(entry);
                
                // 自动滚动到最新条目
                this.thoughtLog.scrollTop = this.thoughtLog.scrollHeight;
                
                // 限制条目数量（保持性能）
                const entries = this.thoughtLog.querySelectorAll('.thought-entry');
                if (entries.length > 100) {
                    entries[0].remove();
                }
            }
        }
        
        // 初始化流式处理器
        const streamProcessor = new StreamProcessor();
        
        // 清空思考日志函数
        function clearThoughtLog() {
            const thoughtLog = document.getElementById('thought-log');
            if (thoughtLog) {
                thoughtLog.innerHTML = `
                    <div class="thought-entry initial">
                        <span class="thought-time">就绪</span>
                        <span class="thought-text">等待您的创意输入...</span>
                    </div>
                `;
            }
        }
        
        // Gradio流式数据处理集成
        function setupGradioStreamingIntegration() {
            // 监听Gradio的stream_data组件变化
            const streamReceiver = document.getElementById('stream-receiver');
            if (streamReceiver) {
                const observer = new MutationObserver((mutations) => {
                    mutations.forEach((mutation) => {
                        if (mutation.type === 'childList' || mutation.type === 'subtree') {
                            try {
                                const textContent = streamReceiver.textContent || streamReceiver.innerText;
                                if (textContent && textContent.trim()) {
                                    const data = JSON.parse(textContent);
                                    if (data && typeof data === 'object') {
                                        console.log('📨 Received stream data:', data);
                                        streamProcessor.processMessage(data);
                                    }
                                }
                            } catch (error) {
                                console.error('❌ Error processing stream data:', error);
                            }
                        }
                    });
                });
                
                observer.observe(streamReceiver, {
                    childList: true,
                    subtree: true,
                    characterData: true
                });
                
                console.log('✅ Gradio streaming integration initialized');
            }
            
            // 监听stream_status变化来启动/停止流式处理
            const streamStatus = document.getElementById('stream-status');
            if (streamStatus) {
                const statusObserver = new MutationObserver((mutations) => {
                    mutations.forEach((mutation) => {
                        const status = streamStatus.textContent || streamStatus.innerText;
                        if (status === 'streaming' && !streamProcessor.isActive) {
                            console.log('🚀 Starting streaming session');
                            streamProcessor.startStreaming();
                        } else if (status === 'completed' && streamProcessor.isActive) {
                            console.log('🎉 Streaming session completed');
                            streamProcessor.finishStreaming();
                        }
                    });
                });
                
                statusObserver.observe(streamStatus, {
                    childList: true,
                    characterData: true
                });
            }
        }
        
        // 模拟流式数据（用于测试）
        function simulateStreamingData() {
            streamProcessor.startStreaming();
            
            // 模拟步骤1
            setTimeout(() => {
                streamProcessor.processMessage({
                    type: 'progress',
                    stage: 'validation',
                    step: 1,
                    title: '🔍 创意验证',
                    progress: 5,
                    data: { detail: '正在解析创意描述' }
                });
            }, 500);
            
            setTimeout(() => {
                streamProcessor.processMessage({
                    type: 'thought',
                    data: { thought: '开始分析您的产品创意，这是一个激动人心的想法！' }
                });
            }, 1000);
            
            setTimeout(() => {
                streamProcessor.processMessage({
                    type: 'action',
                    data: { action: '验证API配置和服务状态' }
                });
            }, 1500);
            
            setTimeout(() => {
                streamProcessor.processMessage({
                    type: 'progress',
                    stage: 'validation',
                    step: 1,
                    title: '🔍 创意验证',
                    progress: 10,
                    data: { detail: '创意验证完成 ✅' }
                });
            }, 2000);
            
            // 可以继续添加更多模拟步骤...
        }
        
        // 增强的Mermaid图表渲染系统
        let chartCache = new Map(); // 图表缓存
        let chartIdCounter = 0;     // 图表ID计数器
        
        function enhancedMermaidRender() {
            const resultContainer = document.getElementById('plan_result');
            if (!resultContainer) return;
            
            // 查找所有Mermaid代码块
            const codeBlocks = resultContainer.querySelectorAll('pre code');
            let hasCharts = false;
            
            codeBlocks.forEach((codeBlock, index) => {
                const code = codeBlock.textContent.trim();
                
                // 检测Mermaid图表类型
                if (code.startsWith('graph') || 
                    code.startsWith('flowchart') || 
                    code.startsWith('gantt') || 
                    code.startsWith('sequenceDiagram') ||
                    code.startsWith('classDiagram') ||
                    code.startsWith('erDiagram')) {
                    
                    hasCharts = true;
                    let finalCode = code;
                    
                    // 特殊处理甘特图：语法验证和修复
                    if (code.startsWith('gantt')) {
                        console.log('🎯 检测到甘特图，执行语法验证...');
                        const validatedCode = validateAndFixGanttChart(code);
                        if (!validatedCode) {
                            console.error('❌ 甘特图语法验证失败，跳过渲染');
                            // 显示错误信息和原始代码
                            codeBlock.parentElement.innerHTML = `
                                <div style="background: #fef2f2; border: 2px solid #fca5a5; border-radius: 0.5rem; padding: 1rem; margin: 1rem 0;">
                                    <p style="color: #dc2626; font-weight: bold; margin-bottom: 0.5rem;">⚠️ 甘特图语法错误</p>
                                    <p style="color: #7f1d1d; margin-bottom: 1rem;">检测到语法问题，无法渲染。请复制以下代码手动修复：</p>
                                    <pre style="background: #f3f4f6; padding: 1rem; border-radius: 0.5rem; overflow-x: auto;"><code>${code}</code></pre>
                                    <button onclick="copyMermaidCode('error-gantt', \\`${code.replace(/`/g, '\\\\`')}\\`)" 
                                            style="background: #dc2626; color: white; border: none; padding: 0.5rem 1rem; border-radius: 0.5rem; cursor: pointer; font-size: 0.9rem; margin-top: 0.5rem;">
                                        📋 复制代码进行修复
                                    </button>
                                </div>
                            `;
                            return;
                        }
                        finalCode = validatedCode;
                        console.log('✅ 甘特图语法验证通过，使用修复后的代码');
                    }
                    
                    const chartId = `mermaid-chart-${++chartIdCounter}`;
                    const cacheKey = `chart-${finalCode.hashCode()}`;
                    
                    // 检查缓存
                    if (!chartCache.has(cacheKey)) {
                        console.log(`🎨 渲染新图表: ${chartId}`);
                        renderMermaidChart(finalCode, chartId, codeBlock.parentElement, cacheKey);
                    } else {
                        console.log(`⚡ 使用缓存图表: ${chartId}`);
                        const cachedHtml = chartCache.get(cacheKey);
                        codeBlock.parentElement.outerHTML = cachedHtml;
                    }
                }
            });
            
            if (hasCharts) {
                console.log('✅ Mermaid图表渲染完成');
            }
        }
        
        function renderMermaidChart(code, chartId, container, cacheKey) {
            try {
                // 创建临时容器
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = `
                    <div class="chart-container" style="margin: 2rem 0; padding: 1.5rem; background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border-radius: 1rem; border: 2px solid #e2e8f0;">
                        <div class="mermaid" id="${chartId}">${code}</div>
                        <div style="text-align: center; margin-top: 1rem;">
                            <button onclick="copyMermaidCode('${chartId}', \\`${code.replace(/`/g, '\\\\`')}\\`)" 
                                    style="background: #3b82f6; color: white; border: none; padding: 0.5rem 1rem; border-radius: 0.5rem; cursor: pointer; font-size: 0.9rem;">
                                📋 复制图表代码
                            </button>
                        </div>
                    </div>
                `;
                
                // 使用Mermaid渲染
                const chartElement = tempDiv.querySelector('.mermaid');
                mermaid.init(undefined, chartElement).then(() => {
                    // 渲染成功，替换原容器并缓存
                    const finalHtml = tempDiv.innerHTML;
                    container.outerHTML = finalHtml;
                    chartCache.set(cacheKey, finalHtml);
                    console.log(`✅ 图表 ${chartId} 渲染成功并已缓存`);
                }).catch((error) => {
                    console.error(`❌ 图表 ${chartId} 渲染失败:`, error);
                    // 渲染失败时显示代码块
                    container.innerHTML = `
                        <div style="background: #fef2f2; border: 2px solid #fca5a5; border-radius: 0.5rem; padding: 1rem; margin: 1rem 0;">
                            <p style="color: #dc2626; font-weight: bold; margin-bottom: 0.5rem;">⚠️ 图表渲染失败</p>
                            <pre style="background: #f3f4f6; padding: 1rem; border-radius: 0.5rem; overflow-x: auto;"><code>${code}</code></pre>
                            <p style="color: #6b7280; font-size: 0.9rem; margin-top: 0.5rem;">请复制上方代码到 Markdown 编辑器中查看图表</p>
                        </div>
                    `;
                });
                
            } catch (error) {
                console.error(`💥 图表渲染过程出错:`, error);
            }
        }
        
        function copyMermaidCode(chartId, code) {
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(code).then(() => {
                    showTempMessage('✅ 图表代码已复制到剪贴板！');
                }).catch(err => {
                    console.error('复制失败:', err);
                    fallbackCopyText(code);
                });
            } else {
                fallbackCopyText(code);
            }
        }
        
        function fallbackCopyText(text) {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                showTempMessage('✅ 图表代码已复制到剪贴板！');
            } catch (err) {
                showTempMessage('❌ 复制失败，请手动选择文本复制');
            }
            document.body.removeChild(textArea);
        }
        
        function showTempMessage(message) {
            const msg = document.createElement('div');
            msg.style.cssText = `
                position: fixed; top: 20px; right: 20px; z-index: 10000;
                background: #10b981; color: white; padding: 1rem 1.5rem;
                border-radius: 0.5rem; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                font-weight: 600; animation: slideIn 0.3s ease-out;
            `;
            msg.textContent = message;
            document.body.appendChild(msg);
            setTimeout(() => msg.remove(), 3000);
        }
        
        // 为String原型添加hashCode方法（用于缓存键）
        String.prototype.hashCode = function() {
            let hash = 0;
            if (this.length === 0) return hash;
            for (let i = 0; i < this.length; i++) {
                const char = this.charCodeAt(i);
                hash = ((hash << 5) - hash) + char;
                hash = hash & hash; // Convert to 32bit integer
            }
            return hash;
        };
        
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
        
        // 智能进度管理系统
        let progressSteps = [
            { id: 'analyzing', icon: '🧠', text: '创意分析', duration: 5 },
            { id: 'researching', icon: '🔍', text: '知识收集', duration: 8 },
            { id: 'planning', icon: '📋', text: '方案生成', duration: 12 },
            { id: 'formatting', icon: '✨', text: '美化输出', duration: 5 }
        ];
        
        let currentStep = 0;
        let progressTimer = null;
        let startTime = null;
        
        function showProgressDisplay() {
            const resultContainer = document.getElementById('plan_result');
            if (!resultContainer) return;
            
            startTime = Date.now();
            currentStep = 0;
            
            const progressHTML = `
                <div class="progress-container">
                    <h3 style="color: #1d4ed8; margin-bottom: 1rem; font-size: 1.3rem;">🚀 AI正在为您创造奇迹</h3>
                    <div class="progress-spinner"></div>
                    <div class="progress-steps">
                        ${progressSteps.map((step, index) => `
                            <div class="progress-step" id="step-${step.id}">
                                <span class="step-icon">${step.icon}</span>
                                <div class="step-text">${step.text}</div>
                            </div>
                        `).join('')}
                    </div>
                    <div class="progress-time" id="progress-time">预计还需 30 秒...</div>
                    <p style="color: #6b7280; margin-top: 1rem; font-size: 0.9rem;">
                        💡 AI正在深度分析您的创意，整合最佳实践，生成专业方案
                    </p>
                </div>
            `;
            
            resultContainer.innerHTML = progressHTML;
            startProgressAnimation();
        }
        
        function startProgressAnimation() {
            if (progressTimer) clearInterval(progressTimer);
            
            // 立即激活第一步
            updateProgressStep(0);
            
            let stepStartTime = Date.now();
            progressTimer = setInterval(() => {
                const elapsed = (Date.now() - startTime) / 1000;
                const currentStepElapsed = (Date.now() - stepStartTime) / 1000;
                
                // 更新时间显示
                const remaining = Math.max(0, 30 - elapsed);
                const timeElement = document.getElementById('progress-time');
                if (timeElement) {
                    if (remaining > 0) {
                        timeElement.textContent = `预计还需 ${Math.ceil(remaining)} 秒...`;
                    } else {
                        timeElement.textContent = `正在完成最后的优化...`;
                    }
                }
                
                // 检查是否需要进入下一步
                if (currentStep < progressSteps.length - 1 && 
                    currentStepElapsed >= progressSteps[currentStep].duration) {
                    currentStep++;
                    updateProgressStep(currentStep);
                    stepStartTime = Date.now();
                }
                
                // 如果超过35秒还没完成，显示延迟提示
                if (elapsed > 35) {
                    const timeElement = document.getElementById('progress-time');
                    if (timeElement) {
                        timeElement.innerHTML = `
                            <span style="color: #f59e0b;">⏳ 正在处理复杂内容，请稍候...</span><br>
                            <span style="font-size: 0.8rem; color: #9ca3af;">复杂创意需要更多时间来生成高质量方案</span>
                        `;
                    }
                }
            }, 1000);
        }
        
        function updateProgressStep(stepIndex) {
            // 标记当前步骤为活跃
            const currentStepElement = document.getElementById(`step-${progressSteps[stepIndex].id}`);
            if (currentStepElement) {
                currentStepElement.classList.add('active');
            }
            
            // 标记之前的步骤为完成
            for (let i = 0; i < stepIndex; i++) {
                const stepElement = document.getElementById(`step-${progressSteps[i].id}`);
                if (stepElement) {
                    stepElement.classList.remove('active');
                    stepElement.classList.add('completed');
                }
            }
        }
        
        function hideProgressDisplay() {
            if (progressTimer) {
                clearInterval(progressTimer);
                progressTimer = null;
            }
            currentStep = 0;
        }
        
        // 为生成按钮绑定进度显示
        function bindProgressToButton() {
            const generateBtn = document.querySelector('.generate-btn');
            if (generateBtn) {
                generateBtn.addEventListener('click', function() {
                    // 延迟显示进度，让Gradio有时间处理
                    setTimeout(showProgressDisplay, 100);
                });
            }
        }
        
        // 监听结果区域变化，自动隐藏进度
        function observeResultChanges() {
            const resultContainer = document.getElementById('plan_result');
            if (!resultContainer) return;
            
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'childList') {
                        // 检查是否显示了实际结果（而不是进度）
                        const hasProgress = resultContainer.querySelector('.progress-container');
                        const hasResult = resultContainer.textContent.includes('开发计划') || 
                                        resultContainer.textContent.includes('技术方案') ||
                                        resultContainer.textContent.includes('❌');
                        
                        if (!hasProgress && hasResult) {
                            hideProgressDisplay();
                        }
                    }
                });
            });
            
            observer.observe(resultContainer, { childList: true, subtree: true });
        }
        
        // 绑定复制按钮事件
        function bindCopyButtons() {
            document.querySelectorAll('.individual-copy-btn').forEach(button => {
                button.addEventListener('click', function() {
                    const promptId = this.getAttribute('data-prompt-id');
                    const promptContent = this.getAttribute('data-prompt-content');
                    copyIndividualPrompt(promptId, promptContent);
                });
            });
        }
        
        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', function() {
            updateMermaidTheme();
            bindCopyButtons();
            bindProgressToButton();
            observeResultChanges();
            
            // 🔥 初始化Gradio流式集成
            setupGradioStreamingIntegration();
            
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
            
            // 监听内容变化，重新绑定复制按钮和渲染图表
            const contentObserver = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'childList') {
                        // 延迟执行，确保DOM更新完成
                        setTimeout(() => {
                            bindCopyButtons();
                            enhancedMermaidRender(); // 自动渲染新的Mermaid图表
                        }, 500);
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
    
    # 主创作区域和流式进度跟踪器布局
    with gr.Row():
        # 左侧：主创作区域 (60%宽度)
        with gr.Column(scale=3, elem_classes="main-creation-canvas"):
            gr.Markdown("## 💡 将您的创意转化为现实", elem_id="input_idea_title")
            
            idea_input = gr.Textbox(
                label="产品创意描述",
                placeholder="🎯 详细描述您的产品创意...\n\n💡 例如：一个智能代码片段管理工具，帮助开发者收集、分类和快速检索常用代码片段。支持多语言语法高亮、标签分类、团队共享功能，并能与主流IDE集成，提高开发效率...\n\n✨ 提示：描述越详细，AI生成的方案越精准！",
                lines=6,
                max_lines=12,
                show_label=False
            )
            
            reference_url_input = gr.Textbox(
                label="参考链接 (可选)",
                placeholder="🔗 粘贴相关网页链接获取更精准的方案（支持GitHub、博客、新闻、文档等）",
                lines=1,
                show_label=True
            )
            
            with gr.Row():
                generate_btn = gr.Button(
                    "🚀 开始创造 - AI生成完整开发方案",
                    variant="primary",
                    size="lg",
                    elem_classes="generate-btn",
                    scale=2
                )
                
                # 🔥 测试流式效果按钮 (开发调试用)
                if config.debug:
                    test_stream_btn = gr.Button(
                        "🧪 测试流式效果",
                        variant="secondary",
                        size="sm",
                        elem_classes="copy-btn",
                        scale=1
                    )
            
            # 简化的快速提示（悬浮显示）
            gr.HTML("""
            <div style="text-align: center; margin-top: 0.5rem;">
                <span style="color: #64748b; font-size: 0.9rem; font-style: italic;">
                    💡 30秒获得专业方案
                </span>
            </div>
            """)
        
        # 右侧：实时进度跟踪器 (40%宽度)
        with gr.Column(scale=2, elem_classes="streaming-tracker-container"):
            # 🔥 实时进度跟踪器
            gr.HTML("""
            <div id="generation-status-tracker" class="tracker-container" style="display: none;">
                <h3 class="tracker-title">🔥 AI工作实况</h3>
                
                <!-- 整体进度条 -->
                <div class="overall-progress">
                    <div class="progress-header">
                        <span class="progress-text">整体进度</span>
                        <span class="progress-percentage">0%</span>
                    </div>
                    <div class="progress-bar-container">
                        <div class="progress-bar" id="overall-progress-bar"></div>
                    </div>
                    <div class="progress-eta">
                        预计完成：<span id="eta-time">计算中...</span>
                    </div>
                </div>
                
                <!-- 6步骤清单 -->
                <div class="steps-checklist">
                    <div class="step-item" data-step="1" data-stage="validation">
                        <div class="step-icon">🔍</div>
                        <div class="step-content">
                            <div class="step-title">创意验证</div>
                            <div class="step-description">解析并验证用户输入的创意</div>
                            <div class="step-status">等待中</div>
                        </div>
                        <div class="step-progress-mini"></div>
                    </div>
                    
                    <div class="step-item" data-step="2" data-stage="knowledge">
                        <div class="step-icon">📚</div>
                        <div class="step-content">
                            <div class="step-title">知识收集</div>
                            <div class="step-description">调用MCP服务获取外部参考资料</div>
                            <div class="step-status">等待中</div>
                        </div>
                        <div class="step-progress-mini"></div>
                    </div>
                    
                    <div class="step-item" data-step="3" data-stage="analysis">
                        <div class="step-icon">🧠</div>
                        <div class="step-content">
                            <div class="step-title">智能分析</div>
                            <div class="step-description">AI深度分析创意可行性和技术方案</div>
                            <div class="step-status">等待中</div>
                        </div>
                        <div class="step-progress-mini"></div>
                    </div>
                    
                    <div class="step-item" data-step="4" data-stage="generation">
                        <div class="step-icon">⚡</div>
                        <div class="step-content">
                            <div class="step-title">方案生成</div>
                            <div class="step-description">生成完整的开发计划和架构设计</div>
                            <div class="step-status">等待中</div>
                        </div>
                        <div class="step-progress-mini"></div>
                    </div>
                    
                    <div class="step-item" data-step="5" data-stage="formatting">
                        <div class="step-icon">✨</div>
                        <div class="step-content">
                            <div class="step-title">内容美化</div>
                            <div class="step-description">格式化内容并生成图表</div>
                            <div class="step-status">等待中</div>
                        </div>
                        <div class="step-progress-mini"></div>
                    </div>
                    
                    <div class="step-item" data-step="6" data-stage="finalization">
                        <div class="step-icon">🎯</div>
                        <div class="step-content">
                            <div class="step-title">最终输出</div>
                            <div class="step-description">创建文件并提取AI编程提示词</div>
                            <div class="step-status">等待中</div>
                        </div>
                        <div class="step-progress-mini"></div>
                    </div>
                </div>
                
                <!-- 当前活动显示 -->
                <div class="current-activity">
                    <div class="activity-header">
                        <span class="activity-icon">🤖</span>
                        <span class="activity-title">当前状态</span>
                    </div>
                    <div class="activity-content" id="current-activity-text">
                        准备开始...
                    </div>
                </div>
            </div>
            """, elem_id="tracker-html")
            
            # 🧠 AI思考过程窗口 (可折叠)
            with gr.Accordion("🧠 AI实时思考日志", open=False, elem_id="thought-viewer"):
                gr.HTML("""
                <div id="thought-log-container" class="thought-container">
                    <div class="thought-header">
                        <span class="thought-icon">💭</span>
                        <span class="thought-title">AI思考过程</span>
                        <button class="clear-log-btn" onclick="clearThoughtLog()">清空</button>
                    </div>
                    <div class="thought-log" id="thought-log">
                        <div class="thought-entry initial">
                            <span class="thought-time">就绪</span>
                            <span class="thought-text">等待您的创意输入...</span>
                        </div>
                    </div>
                </div>
                """, elem_id="thought-html")
            
            # 🔥 流式数据接收器 (隐藏组件) - 核心数据传输通道
            stream_data = gr.JSON(
                value={}, 
                visible=False, 
                elem_id="stream-receiver",
                show_label=False
            )
            stream_status = gr.Textbox(
                value="", 
                visible=False, 
                elem_id="stream-status",
                show_label=False
            )
    
    # 结果显示区域
    with gr.Column(elem_classes="result-container"):
        plan_output = gr.Markdown(
            value="""
<div style="text-align: center; padding: 2.5rem; background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); border-radius: 1.5rem; border: 2px dashed #cbd5e0;">
    <div style="font-size: 3.5rem; margin-bottom: 1.5rem;">✨</div>
    <h3 style="color: #2b6cb0; margin-bottom: 1rem; font-weight: bold; font-size: 1.8rem;">让想法变成现实</h3>
    <p style="color: #4a5568; font-size: 1.2rem; margin-bottom: 2rem; line-height: 1.6;">
        💡 <strong style="color: #e53e3e;">描述您的创意，AI将在30秒内生成完整的实现方案</strong>
    </p>
    <div style="background: linear-gradient(90deg, #edf2f7 0%, #e6fffa 100%); padding: 1.5rem; border-radius: 1rem; margin: 1.5rem 0; border-left: 4px solid #38b2ac;">
        <p style="color: #2c7a7b; margin: 0; font-weight: 600; font-size: 1.1rem;">
            🎯 <strong style="color: #d69e2e;">一站式方案：</strong><span style="color: #e53e3e;">技术架构</span> • <span style="color: #38a169;">开发路线</span> • <span style="color: #3182ce;">部署指南</span> • <span style="color: #805ad5;">AI助手代码</span>
        </p>
    </div>
    <p style="color: #a0aec0; font-size: 1rem; margin-top: 2rem;">
        准备好了吗？点击 <span style="color: #e53e3e; font-weight: bold;">"🚀 开始创造"</span> 按钮，见证创意的力量
    </p>
</div>
            """,
            elem_id="plan_result",
            label="AI生成的开发计划"
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
            💡 <strong style="color: #0d47a1;">使用提示</strong>: 点击上方按钮复制内容到剪贴板，或使用下方下载功能保存为文件。
        </div>
        """)
        
    # 示例区域
    gr.Markdown("## 🎯 快速开始示例", elem_id="quick_start_container")
    gr.Examples(
        examples=[
            # 单MCP服务示例 - 使用真实可访问的链接
            [
                "我想开发一个智能投资助手，能够分析股票、基金数据，提供个性化投资建议和风险评估",
                "https://docs.python.org/3/library/sqlite3.html"
            ],
            # 双MCP服务示例 - 使用真实GitHub项目
            [
                "创建一个在线教育平台，支持视频直播、作业批改、学习进度跟踪和师生互动功能",
                "https://github.com/microsoft/vscode"
            ],
            # 三MCP服务示例 - 使用真实文档链接
            [
                "开发一个数字藏品交易平台，支持NFT铸造、拍卖、展示和社区交流功能",
                "https://ethereum.org/en/developers/docs/"
            ],
            # 通用网页MCP示例 - 使用权威机构链接
            [
                "构建一个智能健康管理系统，包含运动记录、饮食分析、健康报告和医生咨询功能",
                "https://www.who.int/health-topics/physical-activity"
            ],
            # 不使用MCP的纯AI示例
            [
                "设计一个家庭理财助手APP，支持记账、预算规划、投资建议和账单提醒功能",
                ""
            ]
        ],
        inputs=[idea_input, reference_url_input],
        label="🎯 快速体验示例 - 展示不同MCP服务集成效果",
        examples_per_page=5,
        elem_id="enhanced_examples"
    )
    
    # 使用说明
    gr.HTML("""
    <div class="prompts-section" id="ai_helper_instructions">
        <h3>🤖 AI编程助手使用说明</h3>
        <p><strong>生成的编程提示词可以直接用于：</strong></p>
        <ul>
            <li>🔵 <strong>Claude Code</strong> - 专业的AI编程助手</li>
            <li>🟢 <strong>GitHub Copilot</strong> - 代码自动补全工具</li>
            <li>🟡 <strong>ChatGPT</strong> - 通用AI助手的编程模式</li>
            <li>🔴 <strong>其他AI编程工具</strong> - 支持提示词输入的工具</li>
        </ul>
        <p><em>💡 建议：复制特定的编程提示词，然后粘贴到您选择的AI编程工具中，获得针对性的代码实现。</em></p>
    </div>
    """)
    
    # 高级设置与系统信息区域 - 技术细节收纳至此
    with gr.Accordion("⚙️ 高级设置与系统信息", open=False):
        with gr.Tabs():
            with gr.Tab("🔧 系统状态"):
                gr.Markdown(f"""
### 📊 当前系统状态

**🤖 AI引擎：** Qwen2.5-72B-Instruct  
**⚡ 响应时间：** ~30秒  
**🔗 服务状态：** {len([s for s in config.get_enabled_mcp_services()])} 个智能服务已启用

### 🛠️ 可用功能
- ✅ 智能创意分析与技术方案生成
- ✅ 多源知识库集成（GitHub、文档、博客等）
- ✅ AI编程助手提示词定制化生成
- ✅ 专业级开发计划与架构图表
- ✅ 一键下载完整文档
                """)
                
            with gr.Tab("🏗️ 技术架构"):
                gr.Markdown("""
### 🎯 VibeDoc Agent 技术特色

**🧠 智能决策引擎：**
- 根据输入类型自动选择最优处理策略
- 多服务协同工作，确保最佳结果质量
- 完善的容错机制，保证稳定性

**🔗 知识融合系统：**
- 实时获取外部知识源
- 智能内容解析与结构化
- AI推理与外部知识深度融合

**📋 专业输出格式：**
- Mermaid流程图、架构图、甘特图自动生成
- 针对不同AI工具的定制化提示词
- 完整的项目文档导出功能
                """)
                
            with gr.Tab("📖 使用指南"):
                gr.Markdown("""
### 💡 获得最佳效果的技巧

**🎯 创意描述建议：**
- 详细说明核心功能（至少10字）
- 明确目标用户群体和使用场景
- 提及技术偏好或约束条件
- 描述期望的商业价值

**🔗 参考链接优化：**
- GitHub项目：获取技术实现参考
- 技术博客：了解行业最佳实践
- 产品文档：学习功能设计思路
- 新闻资讯：把握市场趋势动态

**⚡ 效率提升：**
- 一次输入多个相关链接效果更佳
- 结合具体的技术栈需求描述
- 明确项目规模和时间预期
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
    
    # 流式生成处理函数
    def process_streaming_generation(user_idea: str, reference_url: str):
        """处理流式生成并返回结果"""
        final_result = None
        stream_messages = []
        
        try:
            # 调用流式生成器
            for message in generate_development_plan_stream(user_idea, reference_url):
                stream_messages.append(message)
                
                # 处理不同类型的消息
                if hasattr(message, 'to_json'):
                    stream_json = message.to_json()
                elif isinstance(message, dict):
                    stream_json = json.dumps(message, ensure_ascii=False)
                else:
                    # 如果是StreamMessage对象，手动序列化
                    stream_json = json.dumps({
                        "type": message.type.value if hasattr(message.type, 'value') else str(message.type),
                        "stage": message.stage.value if hasattr(message.stage, 'value') else str(message.stage),
                        "step": message.step,
                        "title": message.title,
                        "progress": message.progress,
                        "timestamp": message.timestamp,
                        "data": message.data
                    }, ensure_ascii=False)
                
                # 推送流式数据到前端
                yield (
                    gr.update(),  # plan_output不变
                    gr.update(),  # prompts_for_copy不变  
                    gr.update(),  # download_file不变
                    stream_json,  # stream_data
                    "streaming"   # stream_status
                )
            
            # 流式完成后，调用原函数获取最终结果
            final_plan, final_prompts, final_file = generate_development_plan(user_idea, reference_url)
            
            yield (
                final_plan,    # plan_output
                final_prompts, # prompts_for_copy
                final_file,    # download_file  
                json.dumps({"type": "complete", "message": "生成完成"}, ensure_ascii=False),  # stream_data
                "completed"    # stream_status
            )
            
        except Exception as e:
            logger.error(f"流式生成错误: {str(e)}")
            # 如果流式生成失败，回退到普通生成
            final_plan, final_prompts, final_file = generate_development_plan(user_idea, reference_url)
            
            yield (
                final_plan,    # plan_output
                final_prompts, # prompts_for_copy
                final_file,    # download_file  
                json.dumps({"type": "error", "message": f"流式生成失败，已回退到常规模式: {str(e)}"}, ensure_ascii=False),
                "error"        # stream_status
            )
    
    # 绑定流式生成事件
    generate_btn.click(
        fn=process_streaming_generation,
        inputs=[idea_input, reference_url_input],
        outputs=[plan_output, prompts_for_copy, download_file, stream_data, stream_status],
        api_name="generate_plan_stream"
    ).then(
        fn=lambda: gr.update(visible=True),
        outputs=[download_file]
    ).then(
        fn=show_download_info,
        outputs=[download_info]
    )
    
    # 🧪 测试流式效果按钮事件 (仅在debug模式下显示)
    if config.debug:
        def test_streaming_effect():
            """测试流式效果的模拟数据"""
            test_messages = [
                {
                    "type": "progress",
                    "stage": "validation", 
                    "step": 1,
                    "title": "🔍 创意验证",
                    "progress": 5,
                    "timestamp": datetime.now().isoformat(),
                    "data": {"detail": "正在解析创意描述"}
                },
                {
                    "type": "thought",
                    "stage": "validation",
                    "step": 0,
                    "title": "AI思考中...",
                    "progress": 0,
                    "timestamp": datetime.now().isoformat(),
                    "data": {"thought": "开始分析您的产品创意，这是一个激动人心的想法！"}
                },
                {
                    "type": "action", 
                    "stage": "validation",
                    "step": 0,
                    "title": "执行中...",
                    "progress": 0,
                    "timestamp": datetime.now().isoformat(),
                    "data": {"action": "验证API配置和服务状态"}
                },
                {
                    "type": "progress",
                    "stage": "validation",
                    "step": 1, 
                    "title": "🔍 创意验证",
                    "progress": 10,
                    "timestamp": datetime.now().isoformat(),
                    "data": {"detail": "创意验证完成 ✅"}
                }
            ]
            
            for msg in test_messages:
                yield (
                    gr.update(),  # plan_output
                    gr.update(),  # prompts_for_copy
                    gr.update(),  # download_file
                    json.dumps(msg, ensure_ascii=False),  # stream_data
                    "streaming"   # stream_status
                )
                time.sleep(1)  # 模拟延迟
            
            # 完成测试
            yield (
                gr.update(value="## 🧪 流式测试完成\n\n测试消息已成功发送到前端进度跟踪器！"),
                gr.update(), 
                gr.update(),
                json.dumps({"type": "complete", "message": "测试完成"}, ensure_ascii=False),
                "completed"
            )
        
        test_stream_btn.click(
            fn=test_streaming_effect,
            inputs=[],
            outputs=[plan_output, prompts_for_copy, download_file, stream_data, stream_status]
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

# 启动应用 - Agent应用模式
if __name__ == "__main__":
    logger.info("🚀 启动VibeDoc Agent应用")
    logger.info(f"🌍 运行环境: {config.environment}")
    logger.info(f"🔧 启用的MCP服务: {[s.name for s in config.get_enabled_mcp_services()]}")
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=config.port,
        share=False,
        show_error=config.debug
    )