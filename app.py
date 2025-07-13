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

🚫 严禁行为（强化版）：
- 🔴 严禁杜撰任何URL链接。如果你不知道真实的链接，请使用占位符 [待补充的真实链接] 代替
- 🔴 绝对不要编造虚假的链接或参考资料
- 🔴 不要生成不存在的URL（如 xxx.com、example.com、blog.csdn.net/username等）
- 🔴 不要创建虚假的GitHub仓库链接（如 github.com/username/project）
- 🔴 不要引用不存在的CSDN博客文章或任何具体的技术博客链接
- 🔴 不要使用任何示例性质的假链接，包括但不限于域名中包含"username"、"example"等占位符的链接

✅ 正确做法（强化版）：
- ✅ 如果没有提供外部参考，直接基于创意进行分析，明确标注"基于AI最佳实践生成"
- ✅ 只引用用户实际提供的参考链接，绝不擅自添加任何链接
- ✅ 当需要引用技术文档时，使用描述而非具体链接：如"参考React官方文档建议"而非具体URL
- ✅ 当外部知识不可用时，明确说明"本方案基于行业最佳实践和AI分析生成，未使用外部链接参考"
- ✅ 如果确实需要提及某个技术资源，使用格式："建议查阅 [技术名称官方文档] 获取最新信息"

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
                
                # 🔥 发送最终结果消息，包含完整数据
                yield generator.emit(StreamMessage(
                    type=StreamMessageType.FINAL,
                    stage=GenerationStage.FINALIZATION,
                    step=6,
                    title="🎉 生成完成",
                    progress=100,
                    timestamp=datetime.now().isoformat(),
                    data={
                        'completed': True,
                        'final_result': (final_plan_text, prompts_section, temp_file),
                        'elapsed_time': time.time() - generator.tracker.total_start_time
                    }
                ))
                
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

🚫 严禁行为（强化版）：
- 🔴 严禁杜撰任何URL链接。如果你不知道真实的链接，请使用占位符 [待补充的真实链接] 代替
- 🔴 绝对不要编造虚假的链接或参考资料
- 🔴 不要生成不存在的URL（如 xxx.com、example.com、blog.csdn.net/username等）
- 🔴 不要创建虚假的GitHub仓库链接（如 github.com/username/project）
- 🔴 不要引用不存在的CSDN博客文章或任何具体的技术博客链接
- 🔴 不要使用任何示例性质的假链接，包括但不限于域名中包含"username"、"example"等占位符的链接

✅ 正确做法（强化版）：
- ✅ 如果没有提供外部参考，直接基于创意进行分析，明确标注"基于AI最佳实践生成"
- ✅ 只引用用户实际提供的参考链接，绝不擅自添加任何链接
- ✅ 当需要引用技术文档时，使用描述而非具体链接：如"参考React官方文档建议"而非具体URL
- ✅ 当外部知识不可用时，明确说明"本方案基于行业最佳实践和AI分析生成，未使用外部链接参考"
- ✅ 如果确实需要提及某个技术资源，使用格式："建议查阅 [技术名称官方文档] 获取最新信息"

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
    """增强Markdown结构，添加卡片化布局和视觉亮点"""
    lines = content.split('\n')
    enhanced_lines = []
    current_section = None
    in_code_block = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # 检测代码块
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            if in_code_block:
                # 代码块开始
                lang = stripped[3:].strip() or 'text'
                enhanced_lines.append('')
                enhanced_lines.append('<div class="code-card">')
                enhanced_lines.append('<div class="code-header">')
                enhanced_lines.append(f'<span class="code-language">{lang}</span>')
                enhanced_lines.append('<button class="copy-code-btn" onclick="copyCode(this)">📋 复制代码</button>')
                enhanced_lines.append('</div>')
                enhanced_lines.append(line)
            else:
                # 代码块结束
                enhanced_lines.append(line)
                enhanced_lines.append('</div>')
                enhanced_lines.append('')
            i += 1
            continue
            
        if in_code_block:
            enhanced_lines.append(line)
            i += 1
            continue
        
        # 检测主要章节标题
        if stripped.startswith('###') and any(keyword in stripped for keyword in ['产品概述', '技术方案', '开发计划', '部署方案', '推广策略']):
            # 关闭前一个卡片
            if current_section:
                enhanced_lines.append('</div>')
                enhanced_lines.append('')
            
            # 确定卡片类型
            card_class = 'content-card'
            card_icon = '📋'
            
            if '产品概述' in stripped:
                card_class += ' product-overview-card'
                card_icon = '🎯'
            elif '技术方案' in stripped:
                card_class += ' tech-solution-card'
                card_icon = '🛠️'
            elif '开发计划' in stripped:
                card_class += ' development-plan-card'
                card_icon = '📅'
            elif '部署方案' in stripped:
                card_class += ' deployment-card'
                card_icon = '🚀'
            elif '推广策略' in stripped:
                card_class += ' deployment-card'
                card_icon = '📈'
            
            # 开始新卡片
            enhanced_lines.append('')
            enhanced_lines.append(f'<div class="{card_class}">')
            enhanced_lines.append('<div class="card-title">')
            enhanced_lines.append(f'<div class="card-icon">{card_icon}</div>')
            enhanced_lines.append(f'<h3>{stripped.replace("###", "").strip()}</h3>')
            enhanced_lines.append('</div>')
            
            current_section = stripped.replace("###", "").strip()
            i += 1
            continue
        
        # 检测AI编程提示词部分
        if '# 🤖 AI编程助手提示词' in stripped or 'AI编程助手提示词' in stripped:
            # 关闭前一个卡片
            if current_section:
                enhanced_lines.append('</div>')
                enhanced_lines.append('')
            
            # AI提示词特殊卡片
            enhanced_lines.append('')
            enhanced_lines.append('<div class="content-card ai-prompts-card">')
            enhanced_lines.append('<div class="card-title">')
            enhanced_lines.append('<div class="card-icon">🤖</div>')
            enhanced_lines.append('<h3>AI编程助手提示词</h3>')
            enhanced_lines.append('</div>')
            enhanced_lines.append('<p>💡 <strong>使用说明</strong>：以下提示词基于您的项目需求定制生成，可直接复制到 Claude Code、GitHub Copilot、ChatGPT 等AI编程工具中使用</p>')
            
            current_section = 'AI编程助手提示词'
            i += 1
            continue
        
        # 处理技术栈列表
        if current_section == '技术方案' and stripped.startswith('- **') and any(tech in stripped for tech in ['前端', '后端', 'AI 模型', '数据库', '缓存', '部署']):
            if '前端' in stripped and not any('tech-stack-tags' in line for line in enhanced_lines[-5:]):
                enhanced_lines.append('<div class="tech-stack-tags">')
            
            tech_name = stripped.split('**')[1] if '**' in stripped else stripped.replace('- ', '')
            tech_value = stripped.split('**')[2].replace(':', '').strip() if len(stripped.split('**')) > 2 else ''
            
            enhanced_lines.append(f'<span class="tech-tag">{tech_name}: {tech_value}</span>')
            
            # 检查是否是最后一个技术栈项
            if i + 1 < len(lines) and not lines[i + 1].strip().startswith('- **'):
                enhanced_lines.append('</div>')
            
            i += 1
            continue
        
        # 处理功能列表
        if current_section == '产品概述' and stripped.startswith('### 📋'):
            enhanced_lines.append('<div class="feature-list">')
            
            # 收集所有功能项
            feature_items = []
            j = i
            while j < len(lines) and lines[j].strip().startswith('### 📋'):
                feature_items.append(lines[j].strip())
                j += 1
            
            # 生成功能卡片
            for feature in feature_items:
                feature_text = feature.replace('### 📋', '').strip()
                feature_parts = feature_text.split('**', 2)
                if len(feature_parts) >= 3:
                    title = feature_parts[1]
                    desc = feature_parts[2].replace(':', '').strip()
                    enhanced_lines.append('<div class="feature-item">')
                    enhanced_lines.append(f'<h4>{title}</h4>')
                    enhanced_lines.append(f'<p>{desc}</p>')
                    enhanced_lines.append('</div>')
            
            enhanced_lines.append('</div>')
            i = j
            continue
        
        # 检测Mermaid图表
        if stripped.startswith('```mermaid'):
            enhanced_lines.append('')
            enhanced_lines.append('<div class="mermaid-card">')
            enhanced_lines.append(line)
            
            # 添加mermaid内容
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                enhanced_lines.append(lines[i])
                i += 1
            
            if i < len(lines):
                enhanced_lines.append(lines[i])  # 结束的```
            
            enhanced_lines.append('</div>')
            enhanced_lines.append('')
            i += 1
            continue
        
        # 其他内容保持原样
        enhanced_lines.append(line)
        i += 1
    
    # 关闭最后一个卡片
    if current_section:
        enhanced_lines.append('</div>')
    
    return '\n'.join(enhanced_lines)

# 现代化UI - 桌面端优化
custom_css = """
/* 🌟 动态情感色彩系统 - 基于项目类型的智能UI适配 */
:root {
    /* 🎨 基础设计变量 */
    --border-radius: 1.5rem;
    --font-size-base: 16px;
    --line-height-base: 1.7;
    --spacing-unit: 1.5rem;
    --transition-smooth: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    
    /* 🔄 默认主题 - 通用创新 */
    --primary-color: #4f46e5;
    --secondary-color: #7c3aed;
    --accent-color: #ec4899;
    --primary-gradient: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 50%, var(--accent-color) 100%);
    --card-shadow: 0 20px 60px rgba(79, 70, 229, 0.15);
    --card-hover-shadow: 0 30px 80px rgba(79, 70, 229, 0.25);
    --text-primary: #1f2937;
    --text-secondary: #6b7280;
    --bg-primary: rgba(255, 255, 255, 0.95);
    --bg-secondary: rgba(248, 250, 252, 0.9);
}

/* 🚀 科技创新主题 - AI、区块链、前沿技术 */
[data-theme="tech"] {
    --primary-color: #0ea5e9;
    --secondary-color: #3b82f6;
    --accent-color: #6366f1;
    --primary-gradient: linear-gradient(135deg, #0ea5e9 0%, #3b82f6 50%, #6366f1 100%);
    --card-shadow: 0 20px 60px rgba(14, 165, 233, 0.15);
    --card-hover-shadow: 0 30px 80px rgba(14, 165, 233, 0.25);
    --bg-primary: rgba(240, 249, 255, 0.95);
    --bg-secondary: rgba(224, 242, 254, 0.9);
}

/* 🌱 健康生活主题 - 健康、环保、生活方式 */
[data-theme="health"] {
    --primary-color: #10b981;
    --secondary-color: #059669;
    --accent-color: #34d399;
    --primary-gradient: linear-gradient(135deg, #10b981 0%, #059669 50%, #34d399 100%);
    --card-shadow: 0 20px 60px rgba(16, 185, 129, 0.15);
    --card-hover-shadow: 0 30px 80px rgba(16, 185, 129, 0.25);
    --bg-primary: rgba(240, 253, 244, 0.95);
    --bg-secondary: rgba(220, 252, 231, 0.9);
}

/* 💰 金融商业主题 - 金融、投资、商业 */
[data-theme="finance"] {
    --primary-color: #f59e0b;
    --secondary-color: #d97706;
    --accent-color: #fbbf24;
    --primary-gradient: linear-gradient(135deg, #f59e0b 0%, #d97706 50%, #fbbf24 100%);
    --card-shadow: 0 20px 60px rgba(245, 158, 11, 0.15);
    --card-hover-shadow: 0 30px 80px rgba(245, 158, 11, 0.25);
    --bg-primary: rgba(255, 251, 235, 0.95);
    --bg-secondary: rgba(254, 243, 199, 0.9);
}

/* 🎨 创意设计主题 - 设计、艺术、创意产业 */
[data-theme="creative"] {
    --primary-color: #ec4899;
    --secondary-color: #be185d;
    --accent-color: #f472b6;
    --primary-gradient: linear-gradient(135deg, #ec4899 0%, #be185d 50%, #f472b6 100%);
    --card-shadow: 0 20px 60px rgba(236, 72, 153, 0.15);
    --card-hover-shadow: 0 30px 80px rgba(236, 72, 153, 0.25);
    --bg-primary: rgba(253, 242, 248, 0.95);
    --bg-secondary: rgba(252, 231, 243, 0.9);
}

/* 🎓 教育学习主题 - 教育、培训、知识分享 */
[data-theme="education"] {
    --primary-color: #8b5cf6;
    --secondary-color: #7c3aed;
    --accent-color: #a78bfa;
    --primary-gradient: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 50%, #a78bfa 100%);
    --card-shadow: 0 20px 60px rgba(139, 92, 246, 0.15);
    --card-hover-shadow: 0 30px 80px rgba(139, 92, 246, 0.25);
    --bg-primary: rgba(245, 243, 255, 0.95);
    --bg-secondary: rgba(237, 233, 254, 0.9);
}

/* 🏠 生活服务主题 - 家居、服务、日常生活 */
[data-theme="lifestyle"] {
    --primary-color: #06b6d4;
    --secondary-color: #0891b2;
    --accent-color: #22d3ee;
    --primary-gradient: linear-gradient(135deg, #06b6d4 0%, #0891b2 50%, #22d3ee 100%);
    --card-shadow: 0 20px 60px rgba(6, 182, 212, 0.15);
    --card-hover-shadow: 0 30px 80px rgba(6, 182, 212, 0.25);
    --bg-primary: rgba(240, 253, 255, 0.95);
    --bg-secondary: rgba(207, 250, 254, 0.9);
}

/* 🎮 娱乐游戏主题 - 游戏、娱乐、社交 */
[data-theme="entertainment"] {
    --primary-color: #f97316;
    --secondary-color: #ea580c;
    --accent-color: #fb923c;
    --primary-gradient: linear-gradient(135deg, #f97316 0%, #ea580c 50%, #fb923c 100%);
    --card-shadow: 0 20px 60px rgba(249, 115, 22, 0.15);
    --card-hover-shadow: 0 30px 80px rgba(249, 115, 22, 0.25);
    --bg-primary: rgba(255, 247, 237, 0.95);
    --bg-secondary: rgba(254, 237, 213, 0.9);
}

/* 🔒 安全隐私主题 - 安全、隐私、数据保护 */
[data-theme="security"] {
    --primary-color: #64748b;
    --secondary-color: #475569;
    --accent-color: #94a3b8;
    --primary-gradient: linear-gradient(135deg, #64748b 0%, #475569 50%, #94a3b8 100%);
    --card-shadow: 0 20px 60px rgba(100, 116, 139, 0.15);
    --card-hover-shadow: 0 30px 80px rgba(100, 116, 139, 0.25);
    --bg-primary: rgba(248, 250, 252, 0.95);
    --bg-secondary: rgba(241, 245, 249, 0.9);
}

/* 全局背景 - 动态主题 */
body, .gradio-container {
    background: var(--primary-gradient) !important;
    transition: var(--transition-smooth) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif !important;
    font-size: var(--font-size-base) !important;
    line-height: var(--line-height-base) !important;
    color: var(--text-primary) !important;
    min-height: 100vh !important;
}

/* 现代化主容器 - 宽屏桌面优化 */
.main-container {
    max-width: 1200px !important;
    margin: 0 auto !important;
    padding: var(--spacing-unit) !important;
    position: relative !important;
}

/* Gradio容器优化 */
.gradio-container {
    max-width: none !important;
    margin: 0 auto !important;
    padding: 0 !important;
}

/* 修复布局问题 */
.gr-column {
    width: 100% !important;
    flex: none !important;
}

/* 现代化页面标题 */
.header-gradient {
    background: var(--bg-primary) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    color: var(--text-primary) !important;
    padding: 3rem !important;
    border-radius: 2rem !important;
    text-align: center !important;
    margin: var(--spacing-unit) auto !important;
    max-width: 1000px !important;
    box-shadow: var(--card-shadow) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    position: relative !important;
    overflow: hidden !important;
    transition: var(--transition-smooth) !important;
}

.header-gradient:hover {
    transform: translateY(-5px) !important;
    box-shadow: var(--card-hover-shadow) !important;
}

.header-gradient::before {
    content: "" !important;
    position: absolute !important;
    top: -50% !important;
    left: -50% !important;
    width: 200% !important;
    height: 200% !important;
    background: linear-gradient(45deg, transparent 40%, rgba(var(--primary-color), 0.1) 50%, transparent 60%) !important;
    animation: modernShine 4s infinite !important;
}

.header-gradient h1 {
    font-size: 2.5rem !important;
    font-weight: 800 !important;
    margin-bottom: 1rem !important;
    background: var(--primary-gradient) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}

.header-gradient p {
    font-size: 1.2rem !important;
    font-weight: 500 !important;
    opacity: 0.8 !important;
    margin: 0.5rem 0 !important;
}

@keyframes modernShine {
    0% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
    100% { transform: translateX(100%) translateY(100%) rotate(45deg); }
}

/* 🎨 现代化输入创作区 - 玻璃态设计 */
.main-creation-canvas {
    max-width: 1000px !important;
    margin: calc(var(--spacing-unit) * 2) auto !important;
    padding: 3rem !important;
    background: var(--bg-primary) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border-radius: 2rem !important;
    box-shadow: var(--card-shadow) !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
    position: relative !important;
    transition: var(--transition-smooth) !important;
}

.main-creation-canvas:hover {
    transform: translateY(-3px) !important;
    box-shadow: var(--card-hover-shadow) !important;
}

/* 🎯 现代化结果展示区 */
.result-container {
    max-width: 1000px !important;
    margin: calc(var(--spacing-unit) * 2) auto !important;
    padding: 3rem !important;
    background: var(--bg-primary) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border-radius: 2rem !important;
    box-shadow: var(--card-shadow) !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
    position: relative !important;
    transition: var(--transition-smooth) !important;
}

.result-container:hover {
    transform: translateY(-2px) !important;
    box-shadow: var(--card-hover-shadow) !important;
}

/* 现代化按钮设计 - 完整实现 */
.generate-btn, button[data-testid="primary-button"] {
    background: linear-gradient(45deg, #4f46e5, #7c3aed, #ec4899) !important;
    border: none !important;
    color: white !important;
    padding: 1.2rem 3rem !important;
    border-radius: 2.5rem !important;
    font-weight: 800 !important;
    font-size: 1.2rem !important;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 10px 30px rgba(79, 70, 229, 0.4), 0 0 0 1px rgba(255,255,255,0.1) inset !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
    position: relative !important;
    overflow: hidden !important;
    cursor: pointer !important;
    transform: perspective(1px) translateZ(0) !important;
    backface-visibility: hidden !important;
}

.generate-btn:hover, button[data-testid="primary-button"]:hover {
    transform: translateY(-4px) scale(1.02) !important;
    box-shadow: 0 15px 40px rgba(79, 70, 229, 0.6), 
                0 5px 15px rgba(124, 58, 237, 0.4),
                0 0 0 1px rgba(255,255,255,0.2) inset !important;
    background: linear-gradient(45deg, #3730a3, #6d28d9, #db2777) !important;
}

.generate-btn:active, button[data-testid="primary-button"]:active {
    transform: translateY(-2px) scale(1.01) !important;
    transition: all 0.1s ease !important;
}

.generate-btn::before, button[data-testid="primary-button"]::before {
    content: "" !important;
    position: absolute !important;
    top: 0 !important;
    left: -100% !important;
    width: 100% !important;
    height: 100% !important;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent) !important;
    transition: left 0.6s ease-out !important;
    z-index: 1 !important;
}

.generate-btn:hover::before, button[data-testid="primary-button"]:hover::before {
    left: 100% !important;
}

.generate-btn::after, button[data-testid="primary-button"]::after {
    content: "✨" !important;
    position: absolute !important;
    right: 1rem !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    font-size: 1.1rem !important;
    opacity: 0 !important;
    transition: all 0.3s ease !important;
    z-index: 2 !important;
}

.generate-btn:hover::after, button[data-testid="primary-button"]:hover::after {
    opacity: 1 !important;
    right: 1.5rem !important;
}

/* 次要按钮样式 */
.copy-btn, button[data-testid="secondary-button"] {
    background: linear-gradient(45deg, #06b6d4, #0891b2) !important;
    border: none !important;
    color: white !important;
    padding: 0.8rem 1.8rem !important;
    border-radius: 1.5rem !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 6px 20px rgba(6, 182, 212, 0.3) !important;
    text-transform: none !important;
    position: relative !important;
    overflow: hidden !important;
}

.copy-btn:hover, button[data-testid="secondary-button"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(6, 182, 212, 0.4) !important;
    background: linear-gradient(45deg, #0891b2, #0e7490) !important;
}

.copy-btn::before, button[data-testid="secondary-button"]::before {
    content: "" !important;
    position: absolute !important;
    top: 0 !important;
    left: -100% !important;
    width: 100% !important;
    height: 100% !important;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent) !important;
    transition: left 0.4s ease !important;
}

.copy-btn:hover::before, button[data-testid="secondary-button"]:hover::before {
    left: 100% !important;
}

/* 输入框现代化样式 */
textarea, input[type="text"] {
    background: rgba(255, 255, 255, 0.9) !important;
    border: 2px solid rgba(79, 70, 229, 0.2) !important;
    border-radius: 1.5rem !important;
    padding: 1.2rem 1.5rem !important;
    font-size: 1rem !important;
    line-height: 1.6 !important;
    transition: all 0.3s ease !important;
    backdrop-filter: blur(10px) !important;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05) !important;
}

textarea:focus, input[type="text"]:focus {
    outline: none !important;
    border-color: rgba(79, 70, 229, 0.6) !important;
    box-shadow: 0 8px 25px rgba(79, 70, 229, 0.15), 
                0 0 0 3px rgba(79, 70, 229, 0.1) !important;
    background: rgba(255, 255, 255, 0.95) !important;
    transform: translateY(-1px) !important;
}

/* 内容淡入动画 */
.main-creation-canvas {
    animation: slideInUp 0.8s ease-out !important;
}

.result-container {
    animation: slideInUp 1s ease-out 0.2s both !important;
}

@keyframes slideInUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* 内容出现动画 */
#plan_result {
    animation: contentFadeIn 1.2s ease-out !important;
}

@keyframes contentFadeIn {
    0% {
        opacity: 0;
        transform: translateY(20px) scale(0.98);
    }
    50% {
        opacity: 0.7;
        transform: translateY(10px) scale(0.99);
    }
    100% {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}

/* 示例区域动画 */
#enhanced_examples {
    animation: slideInUp 1.4s ease-out 0.4s both !important;
}

/* 悬浮效果增强 */
.main-creation-canvas:hover,
.result-container:hover {
    transform: translateY(-5px) !important;
    box-shadow: var(--card-hover-shadow) !important;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

/* Gradio组件样式优化 */
.gr-button {
    border-radius: 1.5rem !important;
    transition: all 0.3s ease !important;
}

.gr-textbox {
    border-radius: 1.5rem !important;
}

/* 加载状态优化 */
.loading-state {
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%) !important;
    border-radius: 1.5rem !important;
    padding: 2rem !important;
    text-align: center !important;
    border: 2px solid #0ea5e9 !important;
    margin: 2rem 0 !important;
    animation: loadingPulse 2s ease-in-out infinite !important;
}

@keyframes loadingPulse {
    0%, 100% {
        transform: scale(1);
        box-shadow: 0 8px 25px rgba(14, 165, 233, 0.2);
    }
    50% {
        transform: scale(1.02);
        box-shadow: 0 12px 35px rgba(14, 165, 233, 0.3);
    }
}

/* 响应式布局优化 */
@media (max-width: 1024px) {
    .main-container {
        max-width: 95% !important;
        padding: 1rem !important;
    }
    
    .header-gradient h1 {
        font-size: 2rem !important;
    }
    
    .generate-btn, button[data-testid="primary-button"] {
        padding: 1rem 2rem !important;
        font-size: 1rem !important;
    }
}

@media (max-width: 768px) {
    .main-creation-canvas,
    .result-container {
        padding: 2rem !important;
        margin: 1rem auto !important;
    }
    
    .header-gradient {
        padding: 2rem !important;
    }
    
    .header-gradient h1 {
        font-size: 1.8rem !important;
    }
    
    .generate-btn, button[data-testid="primary-button"] {
        padding: 0.9rem 1.5rem !important;
        font-size: 0.95rem !important;
    }
}

/* 滚动条美化 */
::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb {
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(135deg, #3730a3, #6d28d9);
/* Stage 3: 内容卡片化样式 */

/* 主要内容卡片容器 */
.content-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.9) 100%) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border-radius: 2rem !important;
    padding: 2.5rem !important;
    margin: 1.5rem 0 !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
    box-shadow: 0 15px 35px rgba(79, 70, 229, 0.1), 
                0 5px 15px rgba(0, 0, 0, 0.08) !important;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
    position: relative !important;
    overflow: hidden !important;
}

.content-card:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 20px 45px rgba(79, 70, 229, 0.15), 
                0 8px 20px rgba(0, 0, 0, 0.12) !important;
}

.content-card::before {
    content: "" !important;
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    height: 4px !important;
    background: linear-gradient(90deg, #4f46e5, #7c3aed, #ec4899) !important;
    border-radius: 2rem 2rem 0 0 !important;
}

/* 产品概述卡片 */
.product-overview-card {
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%) !important;
    border-left: 5px solid #0ea5e9 !important;
}

.product-overview-card::before {
    background: linear-gradient(90deg, #0ea5e9, #0284c7, #0369a1) !important;
}

/* 技术方案卡片 */
.tech-solution-card {
    background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%) !important;
    border-left: 5px solid #22c55e !important;
}

.tech-solution-card::before {
    background: linear-gradient(90deg, #22c55e, #16a34a, #15803d) !important;
}

/* 开发计划卡片 */
.development-plan-card {
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%) !important;
    border-left: 5px solid #f59e0b !important;
}

.development-plan-card::before {
    background: linear-gradient(90deg, #f59e0b, #d97706, #b45309) !important;
}

/* 部署方案卡片 */
.deployment-card {
    background: linear-gradient(135deg, #fdf2f8 0%, #fce7f3 100%) !important;
    border-left: 5px solid #ec4899 !important;
}

.deployment-card::before {
    background: linear-gradient(90deg, #ec4899, #db2777, #be185d) !important;
}

/* AI编程提示词卡片 */
.ai-prompts-card {
    background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%) !important;
    border-left: 5px solid #8b5cf6 !important;
}

.ai-prompts-card::before {
    background: linear-gradient(90deg, #8b5cf6, #7c3aed, #6d28d9) !important;
}

/* 卡片标题样式 */
.card-title {
    display: flex !important;
    align-items: center !important;
    margin-bottom: 1.5rem !important;
    padding-bottom: 1rem !important;
    border-bottom: 2px solid rgba(0, 0, 0, 0.1) !important;
}

.card-title h2 {
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    margin: 0 !important;
    background: linear-gradient(135deg, #1f2937, #4f46e5) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}

.card-title h3 {
    font-size: 1.5rem !important;
    font-weight: 600 !important;
    margin: 0 !important;
    color: #374151 !important;
}

.card-icon {
    font-size: 2rem !important;
    margin-right: 1rem !important;
    width: 3rem !important;
    height: 3rem !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    border-radius: 50% !important;
    background: linear-gradient(135deg, rgba(79, 70, 229, 0.1), rgba(124, 58, 237, 0.1)) !important;
}

/* 技术栈标签 */
.tech-stack-tags {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 0.75rem !important;
    margin: 1rem 0 !important;
}

.tech-tag {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    color: white !important;
    padding: 0.5rem 1rem !important;
    border-radius: 1.5rem !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3) !important;
    transition: all 0.3s ease !important;
}

.tech-tag:hover {
    transform: translateY(-1px) scale(1.05) !important;
    box-shadow: 0 6px 16px rgba(79, 70, 229, 0.4) !important;
}

/* 功能列表样式 */
.feature-list {
    display: grid !important;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)) !important;
    gap: 1rem !important;
    margin: 1.5rem 0 !important;
}

.feature-item {
    background: rgba(255, 255, 255, 0.7) !important;
    padding: 1.5rem !important;
    border-radius: 1rem !important;
    border: 2px solid rgba(79, 70, 229, 0.1) !important;
    transition: all 0.3s ease !important;
}

.feature-item:hover {
    border-color: rgba(79, 70, 229, 0.3) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 20px rgba(79, 70, 229, 0.15) !important;
}

.feature-item h4 {
    color: #4f46e5 !important;
    margin-bottom: 0.5rem !important;
    font-weight: 600 !important;
}

/* Mermaid图表卡片化 */
.mermaid-card {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%) !important;
    border-radius: 1.5rem !important;
    padding: 2rem !important;
    margin: 2rem 0 !important;
    border: 2px solid #e2e8f0 !important;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08) !important;
    position: relative !important;
}

.mermaid-card::before {
    content: "📊" !important;
    position: absolute !important;
    top: -1rem !important;
    left: 2rem !important;
    background: linear-gradient(135deg, #3b82f6, #1d4ed8) !important;
    color: white !important;
    padding: 0.8rem !important;
    border-radius: 50% !important;
    font-size: 1.2rem !important;
    box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4) !important;
}

/* 代码块增强样式 */
.code-card {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
    border-radius: 1rem !important;
    margin: 1.5rem 0 !important;
    overflow: hidden !important;
    border: 1px solid #334155 !important;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3) !important;
}

.code-header {
    background: linear-gradient(135deg, #1e293b, #334155) !important;
    padding: 1rem 1.5rem !important;
    border-bottom: 1px solid #475569 !important;
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
}

.code-language {
    color: #94a3b8 !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}

.copy-code-btn {
    background: linear-gradient(45deg, #3b82f6, #1d4ed8) !important;
    color: white !important;
    border: none !important;
    padding: 0.5rem 1rem !important;
    border-radius: 0.5rem !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
}

.copy-code-btn:hover {
    background: linear-gradient(45deg, #1d4ed8, #1e40af) !important;
    transform: translateY(-1px) !important;
}

/* 加载状态卡片 */
.loading-card {
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%) !important;
    border-radius: 2rem !important;
    padding: 3rem !important;
    text-align: center !important;
    border: 2px solid #0ea5e9 !important;
    margin: 2rem 0 !important;
    animation: loadingPulse 2s ease-in-out infinite !important;
}

.loading-icon {
    font-size: 3rem !important;
    margin-bottom: 1.5rem !important;
    animation: bounce 2s infinite !important;
}

@keyframes bounce {
    0%, 20%, 50%, 80%, 100% {
        transform: translateY(0);
    }
    40% {
        transform: translateY(-10px);
    }
    60% {
        transform: translateY(-5px);
    }
}

/* Dark模式下的卡片样式 */
.dark .content-card {
    background: linear-gradient(135deg, rgba(45, 55, 72, 0.95) 0%, rgba(31, 41, 55, 0.9) 100%) !important;
    border-color: rgba(75, 85, 99, 0.3) !important;
    color: #f8fafc !important;
}

.dark .feature-item {
    background: rgba(45, 55, 72, 0.7) !important;
    color: #f8fafc !important;
}

.dark .card-title h2,
.dark .card-title h3 {
    color: #f8fafc !important;
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

@keyframes fadeInScale {
    from {
        opacity: 0;
        transform: translate(-50%, -50%) scale(0.8);
    }
    to {
        opacity: 1;
        transform: translate(-50%, -50%) scale(1);
    }
}

/* 🧠 智能提示系统动画 */
@keyframes slideInRight {
    from {
        opacity: 0;
        transform: translateX(100%);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* 智能建议框样式增强 */
.smart-suggestions {
    animation: fadeInUp 0.3s ease-out;
}

.suggestion-item {
    animation: fadeInUp 0.3s ease-out;
    animation-fill-mode: both;
}

.suggestion-item:nth-child(1) { animation-delay: 0.1s; }
.suggestion-item:nth-child(2) { animation-delay: 0.2s; }
.suggestion-item:nth-child(3) { animation-delay: 0.3s; }

/* 响应式优化 */
@media (max-width: 768px) {
    .smart-suggestions {
        position: fixed;
        top: auto;
        bottom: 2rem;
        left: 1rem;
        right: 1rem;
        margin-top: 0;
    }
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

/* 🎨 主题切换动画系统 */
.theme-switching {
    transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

.theme-switching * {
    transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

/* 主题切换通知样式 */
.theme-notification {
    position: fixed;
    top: 2rem;
    right: 2rem;
    z-index: 10000;
    background: var(--bg-primary);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-radius: 1rem;
    box-shadow: var(--card-shadow);
    border: 1px solid rgba(255,255,255,0.3);
    padding: 1rem 1.5rem;
    transform: translateX(100%);
    opacity: 0;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    pointer-events: none;
}

.theme-notification.show {
    transform: translateX(0);
    opacity: 1;
}

.theme-notification-content {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.theme-icon {
    font-size: 1.5rem;
    line-height: 1;
}

.theme-text {
    font-weight: 600;
    color: var(--text-primary);
    font-size: 0.9rem;
    white-space: nowrap;
}

/* 智能主题适配指示器 */
.theme-indicator {
    position: fixed;
    bottom: 2rem;
    left: 2rem;
    z-index: 9999;
    background: var(--bg-primary);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-radius: 50%;
    width: 3rem;
    height: 3rem;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    box-shadow: var(--card-shadow);
    border: 1px solid rgba(255,255,255,0.3);
    transition: var(--transition-smooth);
    cursor: pointer;
}

.theme-indicator:hover {
    transform: scale(1.1);
    box-shadow: var(--card-hover-shadow);
}

/* 🎯 色彩心理学解释通知样式 */
.psychology-explanation {
    position: fixed;
    top: 2rem;
    left: 50%;
    transform: translateX(-50%);
    z-index: 10001;
    pointer-events: auto;
    animation: psychologySlideIn 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.psychology-notification {
    background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(248,250,252,0.9) 100%);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-radius: 1.2rem;
    box-shadow: 0 20px 60px rgba(0,0,0,0.15), 0 0 0 1px rgba(255,255,255,0.5);
    padding: 1.5rem 2rem;
    max-width: 500px;
    min-width: 350px;
    position: relative;
    display: flex;
    align-items: center;
    gap: 1rem;
    transition: all 0.3s ease;
}

.psychology-notification:hover {
    transform: translateY(-2px);
    box-shadow: 0 25px 80px rgba(0,0,0,0.2), 0 0 0 1px rgba(255,255,255,0.6);
}

.psychology-icon {
    font-size: 2rem;
    line-height: 1;
    animation: psychologyPulse 2s infinite;
}

.psychology-content {
    flex: 1;
}

.psychology-title {
    font-weight: 700;
    font-size: 1rem;
    color: var(--text-primary);
    margin-bottom: 0.5rem;
    background: var(--primary-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.psychology-description {
    font-size: 0.85rem;
    color: var(--text-secondary);
    line-height: 1.4;
    margin-bottom: 0.4rem;
}

.psychology-emotions {
    font-size: 0.75rem;
    color: var(--text-secondary);
    opacity: 0.8;
    font-weight: 500;
}

.psychology-close {
    position: absolute;
    top: 0.5rem;
    right: 0.75rem;
    background: none;
    border: none;
    font-size: 1.2rem;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 50%;
    transition: all 0.2s ease;
    line-height: 1;
    width: 1.5rem;
    height: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
}

.psychology-close:hover {
    background: rgba(0,0,0,0.1);
    color: var(--text-primary);
    transform: scale(1.1);
}

/* Dark模式下的心理学通知样式 */
.dark .psychology-notification {
    background: linear-gradient(135deg, rgba(45,55,72,0.95) 0%, rgba(26,32,44,0.9) 100%);
    box-shadow: 0 20px 60px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.1);
}

.dark .psychology-notification:hover {
    box-shadow: 0 25px 80px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.2);
}

.dark .psychology-title {
    color: #F7FAFC;
}

.dark .psychology-description {
    color: #E2E8F0;
}

.dark .psychology-emotions {
    color: #A0AEC0;
}

.dark .psychology-close {
    color: #A0AEC0;
}

.dark .psychology-close:hover {
    background: rgba(255,255,255,0.1);
    color: #F7FAFC;
}

/* 心理学通知动画 */
@keyframes psychologySlideIn {
    0% {
        opacity: 0;
        transform: translateX(-50%) translateY(-20px);
    }
    100% {
        opacity: 1;
        transform: translateX(-50%) translateY(0);
    }
}

@keyframes psychologyPulse {
    0%, 100% {
        transform: scale(1);
    }
    50% {
        transform: scale(1.1);
    }
}

/* 响应式设计 */
@media (max-width: 768px) {
    .psychology-explanation {
        left: 1rem;
        right: 1rem;
        transform: none;
        top: 1rem;
    }
    
    .psychology-notification {
        min-width: auto;
        padding: 1rem 1.5rem;
    }
    
    .psychology-title {
        font-size: 0.9rem;
    }
    
    .psychology-description {
        font-size: 0.8rem;
    }
}

/* 🎭 AI思维可视化系统样式 */
.ai-thinking-container {
    position: fixed;
    top: 50%;
    right: 2rem;
    transform: translateY(-50%);
    width: 400px;
    max-height: 70vh;
    background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(248,250,252,0.9) 100%);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-radius: 1.5rem;
    box-shadow: 0 25px 80px rgba(0,0,0,0.15), 0 0 0 1px rgba(255,255,255,0.5);
    border: 1px solid rgba(255,255,255,0.3);
    z-index: 9998;
    transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    overflow: hidden;
}

.ai-thinking-container.hidden {
    opacity: 0;
    transform: translateY(-50%) translateX(100%);
    pointer-events: none;
}

.ai-thinking-container.visible {
    opacity: 1;
    transform: translateY(-50%) translateX(0);
    pointer-events: auto;
}

.thinking-header {
    background: var(--primary-gradient);
    padding: 1rem 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-radius: 1.5rem 1.5rem 0 0;
    position: relative;
}

.thinking-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: white;
    font-weight: 700;
    font-size: 1rem;
}

.thinking-icon {
    font-size: 1.2rem;
    animation: thinkingPulse 2s infinite;
}

.thinking-controls {
    display: flex;
    gap: 0.5rem;
}

.thinking-toggle,
.thinking-close {
    background: rgba(255,255,255,0.2);
    border: none;
    color: white;
    width: 2rem;
    height: 2rem;
    border-radius: 50%;
    cursor: pointer;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.9rem;
}

.thinking-toggle:hover,
.thinking-close:hover {
    background: rgba(255,255,255,0.3);
    transform: scale(1.1);
}

.thinking-content {
    padding: 1.5rem;
    max-height: calc(70vh - 4rem);
    overflow-y: auto;
    transition: all 0.4s ease;
}

.thinking-content.collapsed {
    max-height: 0;
    padding: 0 1.5rem;
    overflow: hidden;
}

/* 思维管道样式 */
.thinking-pipeline {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.5rem;
    padding: 1rem;
    background: rgba(248,250,252,0.5);
    border-radius: 1rem;
    border: 1px solid rgba(0,0,0,0.05);
}

.pipeline-stage {
    text-align: center;
    transition: all 0.4s ease;
    position: relative;
    padding: 0.5rem;
    border-radius: 0.75rem;
    min-width: 70px;
}

.pipeline-stage.active {
    background: var(--primary-gradient);
    color: white;
    transform: scale(1.05);
    box-shadow: 0 8px 25px rgba(79, 70, 229, 0.3);
}

.pipeline-stage.completed {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: white;
}

.stage-icon {
    font-size: 1.5rem;
    margin-bottom: 0.25rem;
}

.stage-label {
    font-size: 0.7rem;
    font-weight: 600;
    margin-bottom: 0.25rem;
}

.stage-status {
    font-size: 0.6rem;
    opacity: 0.8;
}

.pipeline-arrow {
    font-size: 1.2rem;
    color: var(--text-secondary);
    margin: 0 0.5rem;
}

/* 思考流样式 */
.thinking-stream {
    margin-bottom: 1.5rem;
}

.stream-header {
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid var(--primary-color);
    font-size: 0.9rem;
}

.stream-content {
    max-height: 200px;
    overflow-y: auto;
    padding: 0.5rem;
    background: rgba(248,250,252,0.5);
    border-radius: 1rem;
    border: 1px solid rgba(0,0,0,0.05);
}

.stream-message {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.75rem;
    margin-bottom: 0.75rem;
    border-radius: 0.75rem;
    border-left: 3px solid var(--primary-color);
    background: white;
    box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    transition: all 0.3s ease;
    position: relative;
}

.stream-message:hover {
    transform: translateX(3px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.1);
}

.stream-message.idle {
    opacity: 0.6;
    font-style: italic;
    border-left-color: var(--text-secondary);
}

.stream-message.analytical {
    border-left-color: #3b82f6;
}

.stream-message.reasoning {
    border-left-color: #8b5cf6;
}

.stream-message.creative {
    border-left-color: #ec4899;
}

.stream-message.optimizing {
    border-left-color: #f59e0b;
}

.stream-message.synthesizing {
    border-left-color: #10b981;
}

.message-icon {
    font-size: 1.2rem;
    line-height: 1;
    margin-top: 0.1rem;
}

.message-content {
    flex: 1;
}

.message-type {
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.25rem;
}

.message-text {
    font-size: 0.85rem;
    color: var(--text-primary);
    line-height: 1.4;
}

.message-timestamp {
    font-size: 0.6rem;
    color: var(--text-secondary);
    opacity: 0.7;
    position: absolute;
    top: 0.5rem;
    right: 0.75rem;
}

/* 思考指标样式 */
.thinking-metrics {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 1rem;
}

.metric-item {
    text-align: center;
    padding: 0.75rem 0.5rem;
    background: rgba(248,250,252,0.5);
    border-radius: 0.75rem;
    border: 1px solid rgba(0,0,0,0.05);
}

.metric-label {
    font-size: 0.7rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    font-weight: 600;
    letter-spacing: 0.5px;
    display: block;
    margin-bottom: 0.5rem;
}

.metric-value {
    font-size: 0.9rem;
    font-weight: 700;
    color: var(--primary-color);
}

.depth-indicator {
    width: 100%;
    height: 4px;
    background: rgba(0,0,0,0.1);
    border-radius: 2px;
    overflow: hidden;
    margin-top: 0.5rem;
}

.depth-bar {
    height: 100%;
    background: var(--primary-gradient);
    border-radius: 2px;
    transition: width 0.6s ease;
    width: 0%;
}

/* Dark模式下的AI思维可视化样式 */
.dark .ai-thinking-container {
    background: linear-gradient(135deg, rgba(45,55,72,0.95) 0%, rgba(26,32,44,0.9) 100%);
    box-shadow: 0 25px 80px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.1);
}

.dark .thinking-pipeline,
.dark .stream-content,
.dark .metric-item {
    background: rgba(26,32,44,0.5);
    border-color: rgba(255,255,255,0.1);
}

.dark .stream-message {
    background: rgba(45,55,72,0.8);
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}

.dark .stream-message:hover {
    box-shadow: 0 6px 20px rgba(0,0,0,0.3);
}

/* 思维可视化动画 */
@keyframes thinkingPulse {
    0%, 100% {
        transform: scale(1);
    }
    50% {
        transform: scale(1.1);
    }
}

/* 响应式设计 */
@media (max-width: 1024px) {
    .ai-thinking-container {
        right: 1rem;
        width: 350px;
    }
}

@media (max-width: 768px) {
    .ai-thinking-container {
        position: fixed;
        top: auto;
        bottom: 1rem;
        right: 1rem;
        left: 1rem;
        width: auto;
        transform: none;
        max-height: 50vh;
    }
    
    .ai-thinking-container.hidden {
        transform: translateY(100%);
    }
    
    .ai-thinking-container.visible {
        transform: translateY(0);
    }
    
    .thinking-pipeline {
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    
    .pipeline-stage {
        min-width: 60px;
    }
    
    .pipeline-arrow {
        display: none;
    }
    
    .thinking-metrics {
        grid-template-columns: 1fr 1fr;
        gap: 0.75rem;
    }
    
    .metric-item:last-child {
        grid-column: 1 / -1;
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
        
        // 极简进度显示系统 - 修复复杂流式系统问题
        function showBasicProgress() {
            const planResult = document.getElementById('plan_result');
            if (planResult) {
                planResult.innerHTML = `
                    <div style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 1rem; padding: 2rem; text-align: center; border: 2px solid #0ea5e9; margin: 1rem 0;">
                        <div style="font-size: 2rem; margin-bottom: 1rem;">🚀</div>
                        <h3 style="color: #1d4ed8; margin-bottom: 1rem;">AI正在生成您的专业方案</h3>
                        <div id="basic-spinner" style="margin: 1.5rem auto; width: 32px; height: 32px; border: 3px solid #e5e7eb; border-top: 3px solid #3b82f6; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                        <p style="color: #6b7280; margin: 0.5rem 0;">预计需要30-100秒，请耐心等待</p>
                        <p style="color: #9ca3af; font-size: 0.9rem;">💡 AI正在深度分析您的创意，生成完整方案</p>
                    </div>
                `;
            }
        }
        
        // 监听生成按钮 - 简化版本
        function bindBasicProgress() {
            const generateBtn = document.querySelector('.generate-btn');
            if (generateBtn) {
                generateBtn.addEventListener('click', function() {
                    setTimeout(showBasicProgress, 50);
                });
            }
        }
        
        // 结果监听 - 简化版
        function observeBasicResults() {
            const planResult = document.getElementById('plan_result');
            if (!planResult) return;
            
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'childList') {
                        const hasContent = planResult.textContent.includes('开发计划') || 
                                         planResult.textContent.includes('技术方案') ||
                                         planResult.textContent.includes('❌') ||
                                         planResult.textContent.includes('生成完成');
                        
                        // 如果有实际内容显示，说明生成完成
                        if (hasContent && !planResult.textContent.includes('AI正在生成')) {
                            console.log('✅ 检测到生成完成');
                        }
                    }
                });
            });
            
            observer.observe(planResult, { childList: true, subtree: true });
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
        
        // 🎨 智能主题检测系统 - 基于用户输入的情感色彩适配
        const THEME_KEYWORDS = {
            'tech': [
                'AI', '人工智能', '机器学习', '深度学习', '算法', '区块链', '智能', '自动化', '云计算', 
                'IoT', '物联网', '大数据', 'VR', 'AR', '虚拟现实', '增强现实', '机器人', '无人机', 
                '科技', '技术', '创新', '前沿', '数字化', '智慧', '自动驾驶', '5G', '边缘计算'
            ],
            'health': [
                '健康', '医疗', '养生', '运动', '健身', '营养', '医生', '医院', '诊断', '治疗',
                '药物', '康复', '预防', '体检', '心理健康', '睡眠', '减肥', '瑜伽', '跑步',
                '饮食', '保健', '疾病', '症状', '护理', '理疗', '中医', '西医', '疫苗'
            ],
            'finance': [
                '金融', '投资', '理财', '银行', '保险', '基金', '股票', '证券', '期货', '外汇',
                '贷款', '信贷', '支付', '财务', '会计', '审计', '税务', '预算', '成本', '利润',
                '风险', '收益', '资产', '负债', '现金流', '上市', 'IPO', '并购', '估值'
            ],
            'creative': [
                '设计', '创意', '艺术', '美术', '绘画', '摄影', '视频', '音乐', '舞蹈', '文学',
                '写作', '创作', '灵感', '想象', '美学', '色彩', '构图', '品牌', '广告', '营销',
                '时尚', '装饰', '建筑', '室内设计', '平面设计', 'UI设计', 'UX设计', '动画'
            ],
            'education': [
                '教育', '学习', '培训', '课程', '教学', '老师', '学生', '学校', '大学', '知识',
                '技能', '考试', '证书', '学位', '研究', '学术', '论文', '图书馆', '在线教育',
                '远程学习', '编程教学', '语言学习', '职业培训', '继续教育', '早教', '成人教育'
            ],
            'lifestyle': [
                '生活', '家居', '装修', '家具', '厨房', '卧室', '客厅', '服务', '便民', '社区',
                '购物', '美食', '餐饮', '旅游', '出行', '交通', '住宿', '娱乐', '休闲', '爱好',
                '宠物', '园艺', '清洁', '维修', '搬家', '租房', '买房', '二手交易'
            ],
            'entertainment': [
                '游戏', '娱乐', '电影', '电视', '综艺', '直播', '短视频', '社交', '聊天', '交友',
                '约会', '婚恋', '社区', '论坛', '博客', '新闻', '资讯', '体育', '竞技', '赛事',
                '音乐', '播客', '小说', '漫画', '动漫', '网红', '明星', '粉丝'
            ],
            'security': [
                '安全', '隐私', '保护', '防护', '加密', '密码', '认证', '授权', '监控', '防火墙',
                '杀毒', '备份', '恢复', '审计', '合规', '风控', '反欺诈', '身份验证', '数据保护',
                '网络安全', '信息安全', '系统安全', '应用安全', '云安全', '移动安全'
            ]
        };
        
        function detectThemeFromText(text) {
            if (!text || text.length < 10) return 'default';
            
            const normalizedText = text.toLowerCase();
            const scores = {};
            
            // 计算每个主题的匹配分数
            for (const [theme, keywords] of Object.entries(THEME_KEYWORDS)) {
                scores[theme] = 0;
                for (const keyword of keywords) {
                    const regex = new RegExp(keyword.toLowerCase(), 'g');
                    const matches = normalizedText.match(regex);
                    if (matches) {
                        scores[theme] += matches.length * keyword.length; // 长关键词权重更高
                    }
                }
            }
            
            // 找到得分最高的主题
            const maxScore = Math.max(...Object.values(scores));
            if (maxScore === 0) return 'default';
            
            const selectedTheme = Object.keys(scores).find(theme => scores[theme] === maxScore);
            
            console.log('🎨 Theme Detection:', {
                text: text.substring(0, 100) + '...',
                scores,
                selectedTheme,
                maxScore
            });
            
            return selectedTheme;
        }
        
        // 🎯 色彩心理学应用系统 - 项目类型自动匹配色彩方案
        class ColorPsychologySystem {
            constructor() {
                this.isActive = false;
                this.currentPsychologyProfile = null;
                
                // 色彩心理学映射 - 基于心理学研究的颜色情感关联
                this.colorPsychologyMap = {
                    // 🔥 激励与动力类项目
                    'motivation': {
                        colors: {
                            primary: '#ff6b6b',    // 热情红 - 激发行动力
                            secondary: '#ee5a24',  // 活力橙 - 促进创造力
                            accent: '#ff9ff3'      // 活跃粉 - 增强表达欲
                        },
                        psychology: '红色系激发行动力和紧迫感，橙色促进创造力和热情',
                        emotions: ['激情', '动力', '决心', '活力'],
                        keywords: ['目标', '挑战', '突破', '成就', '梦想', '奋斗', '坚持', '成功']
                    },
                    
                    // 🧘 冷静与专注类项目  
                    'focus': {
                        colors: {
                            primary: '#0984e3',    // 专注蓝 - 提升集中力
                            secondary: '#6c5ce7',  // 智慧紫 - 促进思考
                            accent: '#00cec9'      // 平静青 - 减少焦虑
                        },
                        psychology: '蓝色系提升专注力和信任感，紫色促进深度思考',
                        emotions: ['专注', '冷静', '理性', '深度'],
                        keywords: ['学习', '研究', '分析', '专业', '精确', '逻辑', '系统', '效率']
                    },
                    
                    // 🌱 成长与发展类项目
                    'growth': {
                        colors: {
                            primary: '#00b894',    // 成长绿 - 象征发展
                            secondary: '#55a3ff',  // 希望蓝 - 代表未来
                            accent: '#fdcb6e'      // 温暖黄 - 带来乐观
                        },
                        psychology: '绿色象征成长和平衡，黄色带来乐观和能量',
                        emotions: ['成长', '希望', '平衡', '乐观'],
                        keywords: ['教育', '培训', '发展', '进步', '提升', '学习', '成长', '未来']
                    },
                    
                    // 💝 关怀与温暖类项目
                    'care': {
                        colors: {
                            primary: '#fd79a8',    // 关爱粉 - 传达温暖
                            secondary: '#fdcb6e',  // 阳光黄 - 带来快乐
                            accent: '#e17055'      // 舒适橙 - 营造安全感
                        },
                        psychology: '粉色传达关爱和接纳，黄色带来快乐和温暖',
                        emotions: ['关爱', '温暖', '安全', '舒适'],
                        keywords: ['健康', '护理', '家庭', '儿童', '老人', '关爱', '温暖', '陪伴']
                    },
                    
                    // ⚡ 创新与前沿类项目
                    'innovation': {
                        colors: {
                            primary: '#6c5ce7',    // 创新紫 - 激发想象
                            secondary: '#74b9ff',  // 科技蓝 - 代表前沿
                            accent: '#00cec9'      // 未来青 - 象征进步
                        },
                        psychology: '紫色激发创造力和想象力，青色代表未来和创新',
                        emotions: ['创新', '前沿', '想象', '突破'],
                        keywords: ['AI', '科技', '创新', '前沿', '未来', '智能', '革命', '突破']
                    },
                    
                    // 💰 信任与稳定类项目
                    'trust': {
                        colors: {
                            primary: '#2d3436',    // 权威黑 - 建立信任
                            secondary: '#0984e3',  // 可靠蓝 - 传达稳定
                            accent: '#00b894'      // 成功绿 - 象征繁荣
                        },
                        psychology: '深色系建立权威感，蓝色传达可靠性和稳定性',
                        emotions: ['信任', '稳定', '权威', '可靠'],
                        keywords: ['金融', '投资', '银行', '保险', '安全', '信任', '专业', '稳定']
                    }
                };
                
                // 情感强度检测关键词
                this.emotionalIntensityWords = {
                    'high': ['革命性', '颠覆', '突破性', '创新性', '前所未有', '划时代', '里程碑'],
                    'medium': ['优化', '改进', '提升', '增强', '完善', '更好', '高效'],
                    'low': ['简单', '基础', '日常', '普通', '标准', '常规', '传统']
                };
                
                // 用户意图分析关键词
                this.userIntentKeywords = {
                    'solve_problem': ['解决', '问题', '困难', '挑战', '痛点', '需求'],
                    'create_value': ['价值', '收益', '利润', '效益', '回报', '成果'],
                    'improve_life': ['生活', '体验', '便利', '舒适', '健康', '幸福'],
                    'express_creativity': ['创意', '表达', '艺术', '设计', '美观', '独特'],
                    'build_community': ['社区', '连接', '分享', '交流', '合作', '团队']
                };
            }
            
            init() {
                this.isActive = true;
                this.bindColorPsychologyDetection();
                console.log('🎯 色彩心理学应用系统已启动');
            }
            
            // 分析文本的心理色彩需求
            analyzePsychologicalColorNeeds(text) {
                if (!text || text.length < 10) return null;
                
                const normalizedText = text.toLowerCase();
                let psychologyScore = {};
                
                // 计算各心理特征的匹配度
                for (const [profileName, profile] of Object.entries(this.colorPsychologyMap)) {
                    psychologyScore[profileName] = 0;
                    
                    // 关键词匹配
                    for (const keyword of profile.keywords) {
                        const regex = new RegExp(keyword, 'gi');
                        const matches = normalizedText.match(regex);
                        if (matches) {
                            psychologyScore[profileName] += matches.length * 2;
                        }
                    }
                    
                    // 情感词匹配
                    for (const emotion of profile.emotions) {
                        if (normalizedText.includes(emotion)) {
                            psychologyScore[profileName] += 3;
                        }
                    }
                }
                
                // 情感强度分析
                const intensity = this.analyzeEmotionalIntensity(normalizedText);
                
                // 用户意图分析
                const intent = this.analyzeUserIntent(normalizedText);
                
                // 找到最匹配的心理色彩方案
                const maxScore = Math.max(...Object.values(psychologyScore));
                if (maxScore === 0) return null;
                
                const selectedProfile = Object.keys(psychologyScore).find(
                    profile => psychologyScore[profile] === maxScore
                );
                
                const result = {
                    profile: selectedProfile,
                    colors: this.colorPsychologyMap[selectedProfile].colors,
                    psychology: this.colorPsychologyMap[selectedProfile].psychology,
                    emotions: this.colorPsychologyMap[selectedProfile].emotions,
                    intensity: intensity,
                    intent: intent,
                    confidence: maxScore / 10, // 置信度
                    allScores: psychologyScore
                };
                
                console.log('🎯 色彩心理学分析结果:', result);
                return result;
            }
            
            // 分析情感强度
            analyzeEmotionalIntensity(text) {
                for (const [level, words] of Object.entries(this.emotionalIntensityWords)) {
                    for (const word of words) {
                        if (text.includes(word)) {
                            return level;
                        }
                    }
                }
                return 'medium';
            }
            
            // 分析用户意图
            analyzeUserIntent(text) {
                let intentScores = {};
                
                for (const [intent, keywords] of Object.entries(this.userIntentKeywords)) {
                    intentScores[intent] = 0;
                    for (const keyword of keywords) {
                        if (text.includes(keyword)) {
                            intentScores[intent]++;
                        }
                    }
                }
                
                const maxScore = Math.max(...Object.values(intentScores));
                if (maxScore === 0) return 'general';
                
                return Object.keys(intentScores).find(intent => intentScores[intent] === maxScore);
            }
            
            // 应用心理色彩方案
            applyPsychologicalColorScheme(profile) {
                if (!profile || !this.colorPsychologyMap[profile.profile]) return;
                
                const colors = profile.colors;
                const intensity = profile.intensity;
                
                // 根据情感强度调整颜色饱和度
                const saturationMultiplier = {
                    'high': 1.2,
                    'medium': 1.0,
                    'low': 0.8
                }[intensity] || 1.0;
                
                // 创建自定义CSS变量
                const root = document.documentElement;
                root.style.setProperty('--psychology-primary', colors.primary);
                root.style.setProperty('--psychology-secondary', colors.secondary);
                root.style.setProperty('--psychology-accent', colors.accent);
                
                // 生成心理导向的渐变
                const psychologyGradient = `linear-gradient(135deg, ${colors.primary} 0%, ${colors.secondary} 50%, ${colors.accent} 100%)`;
                root.style.setProperty('--psychology-gradient', psychologyGradient);
                
                // 应用到页面背景
                document.body.style.background = psychologyGradient;
                document.body.style.transition = 'all 1.2s cubic-bezier(0.4, 0, 0.2, 1)';
                
                // 显示心理色彩解释
                this.showPsychologyExplanation(profile);
                
                // 记录应用的心理方案
                this.currentPsychologyProfile = profile;
            }
            
            // 显示心理色彩解释
            showPsychologyExplanation(profile) {
                // 创建解释提示
                const explanation = document.createElement('div');
                explanation.className = 'psychology-explanation';
                explanation.innerHTML = `
                    <div class="psychology-notification">
                        <div class="psychology-icon">🎯</div>
                        <div class="psychology-content">
                            <div class="psychology-title">智能色彩心理学应用</div>
                            <div class="psychology-description">${profile.psychology}</div>
                            <div class="psychology-emotions">
                                情感特征: ${profile.emotions.join(' • ')}
                            </div>
                        </div>
                        <button class="psychology-close" onclick="this.parentElement.style.display='none'">×</button>
                    </div>
                `;
                
                // 添加到页面
                document.body.appendChild(explanation);
                
                // 3秒后自动消失
                setTimeout(() => {
                    if (explanation.parentElement) {
                        explanation.style.opacity = '0';
                        setTimeout(() => explanation.remove(), 500);
                    }
                }, 3000);
            }
            
            // 绑定色彩心理学检测
            bindColorPsychologyDetection() {
                const userIdea = document.getElementById('user_idea');
                if (!userIdea) return;
                
                let debounceTimer;
                userIdea.addEventListener('input', (e) => {
                    clearTimeout(debounceTimer);
                    debounceTimer = setTimeout(() => {
                        const text = e.target.value;
                        if (text.length > 20) { // 有足够内容才进行分析
                            const psychologyProfile = this.analyzePsychologicalColorNeeds(text);
                            if (psychologyProfile && psychologyProfile.confidence > 2) {
                                this.applyPsychologicalColorScheme(psychologyProfile);
                            }
                        }
                    }, 1000); // 1秒防抖
                });
            }
            
            // 重置到默认颜色方案
            resetToDefaultColors() {
                const root = document.documentElement;
                root.style.removeProperty('--psychology-primary');
                root.style.removeProperty('--psychology-secondary'); 
                root.style.removeProperty('--psychology-accent');
                root.style.removeProperty('--psychology-gradient');
                
                // 恢复默认主题
                document.body.style.background = '';
                this.currentPsychologyProfile = null;
            }
            
            // 获取当前心理色彩方案
            getCurrentPsychologyProfile() {
                return this.currentPsychologyProfile;
            }
        }
        
        // 🎭 实时思维可视化系统 - 展示AI思考过程和决策逻辑
        class AIThinkingVisualizationSystem {
            constructor() {
                this.isActive = false;
                this.thinkingContainer = null;
                this.currentThoughts = [];
                this.thinkingSpeed = 80; // 文字显示速度(毫秒)
                
                // AI思维模式配置
                this.thinkingModes = {
                    'analyzing': {
                        icon: '🔍',
                        color: '#3b82f6',
                        title: '分析阶段',
                        style: 'analytical'
                    },
                    'reasoning': {
                        icon: '🧠',
                        color: '#8b5cf6',
                        title: '推理阶段',
                        style: 'reasoning'
                    },
                    'creating': {
                        icon: '✨',
                        color: '#ec4899',
                        title: '创造阶段',
                        style: 'creative'
                    },
                    'optimizing': {
                        icon: '⚡',
                        color: '#f59e0b',
                        title: '优化阶段',
                        style: 'optimizing'
                    },
                    'synthesizing': {
                        icon: '🔗',
                        color: '#10b981',
                        title: '综合阶段',
                        style: 'synthesizing'
                    }
                };
                
                // AI思考步骤模板
                this.thinkingPatterns = {
                    'project_analysis': [
                        { mode: 'analyzing', thought: '正在分析项目核心需求和目标用户群体...' },
                        { mode: 'reasoning', thought: '基于市场调研数据推理最佳技术栈选择...' },
                        { mode: 'analyzing', thought: '评估项目复杂度和开发周期预估...' },
                        { mode: 'creating', thought: '构建创新的产品架构设计方案...' },
                        { mode: 'optimizing', thought: '优化用户体验流程和界面设计...' },
                        { mode: 'synthesizing', thought: '整合所有分析结果生成完整开发计划...' }
                    ],
                    'mcp_integration': [
                        { mode: 'analyzing', thought: '检测项目类型，选择最适合的MCP服务...' },
                        { mode: 'reasoning', thought: '根据外部知识源优化技术方案...' },
                        { mode: 'synthesizing', thought: '融合多个MCP服务的专业建议...' }
                    ],
                    'ai_enhancement': [
                        { mode: 'creating', thought: '生成个性化的AI编程助手提示词...' },
                        { mode: 'optimizing', thought: '根据项目特点调整提示词精确度...' },
                        { mode: 'synthesizing', thought: '确保提示词与开发计划完美匹配...' }
                    ]
                };
                
                // 思维可视化元素配置
                this.visualElements = {
                    'neural_network': '🕸️ 神经网络激活中...',
                    'decision_tree': '🌳 决策树分析中...',
                    'pattern_matching': '🎯 模式匹配处理中...',
                    'knowledge_graph': '📊 知识图谱构建中...',
                    'semantic_analysis': '📝 语义分析进行中...',
                    'context_awareness': '🎭 上下文感知中...'
                };
            }
            
            init() {
                this.isActive = true;
                this.createThinkingContainer();
                this.bindToGenerationProcess();
                console.log('🎭 AI思维可视化系统已启动');
            }
            
            // 创建思维可视化容器
            createThinkingContainer() {
                // 移除已存在的容器
                const existing = document.getElementById('ai-thinking-container');
                if (existing) existing.remove();
                
                const container = document.createElement('div');
                container.id = 'ai-thinking-container';
                container.className = 'ai-thinking-container hidden';
                container.innerHTML = `
                    <div class="thinking-header">
                        <div class="thinking-title">
                            <span class="thinking-icon">🎭</span>
                            <span class="thinking-text">AI思维过程实时展示</span>
                        </div>
                        <div class="thinking-controls">
                            <button class="thinking-toggle" title="展开/收起">📍</button>
                            <button class="thinking-close" title="关闭">×</button>
                        </div>
                    </div>
                    <div class="thinking-content">
                        <div class="thinking-pipeline">
                            <div class="pipeline-stage" data-stage="input">
                                <div class="stage-icon">📝</div>
                                <div class="stage-label">用户输入</div>
                                <div class="stage-status">待处理</div>
                            </div>
                            <div class="pipeline-arrow">→</div>
                            <div class="pipeline-stage" data-stage="analysis">
                                <div class="stage-icon">🔍</div>
                                <div class="stage-label">需求分析</div>
                                <div class="stage-status">待处理</div>
                            </div>
                            <div class="pipeline-arrow">→</div>
                            <div class="pipeline-stage" data-stage="reasoning">
                                <div class="stage-icon">🧠</div>
                                <div class="stage-label">逻辑推理</div>
                                <div class="stage-status">待处理</div>
                            </div>
                            <div class="pipeline-arrow">→</div>
                            <div class="pipeline-stage" data-stage="creation">
                                <div class="stage-icon">✨</div>
                                <div class="stage-label">方案生成</div>
                                <div class="stage-status">待处理</div>
                            </div>
                        </div>
                        <div class="thinking-stream">
                            <div class="stream-header">实时思考流</div>
                            <div class="stream-content" id="thinking-stream-content">
                                <div class="stream-message idle">等待AI开始思考...</div>
                            </div>
                        </div>
                        <div class="thinking-metrics">
                            <div class="metric-item">
                                <span class="metric-label">处理速度</span>
                                <span class="metric-value" id="processing-speed">0 tok/s</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-label">思考深度</span>
                                <div class="depth-indicator">
                                    <div class="depth-bar" id="thinking-depth"></div>
                                </div>
                            </div>
                            <div class="metric-item">
                                <span class="metric-label">创新指数</span>
                                <span class="metric-value" id="innovation-score">--</span>
                            </div>
                        </div>
                    </div>
                `;
                
                document.body.appendChild(container);
                this.thinkingContainer = container;
                
                // 绑定控制事件
                this.bindContainerEvents();
            }
            
            // 绑定容器事件
            bindContainerEvents() {
                const toggleBtn = this.thinkingContainer.querySelector('.thinking-toggle');
                const closeBtn = this.thinkingContainer.querySelector('.thinking-close');
                const content = this.thinkingContainer.querySelector('.thinking-content');
                
                toggleBtn.addEventListener('click', () => {
                    content.classList.toggle('collapsed');
                    toggleBtn.textContent = content.classList.contains('collapsed') ? '📌' : '📍';
                });
                
                closeBtn.addEventListener('click', () => {
                    this.hideThinking();
                });
            }
            
            // 绑定到生成过程
            bindToGenerationProcess() {
                const generateBtn = document.getElementById('generate_btn');
                if (!generateBtn) return;
                
                // 监听生成按钮点击
                generateBtn.addEventListener('click', () => {
                    setTimeout(() => {
                        this.startThinkingVisualization();
                    }, 500);
                });
            }
            
            // 开始思维可视化
            startThinkingVisualization() {
                this.showThinking();
                this.resetPipeline();
                this.startThinkingSequence();
            }
            
            // 显示思维容器
            showThinking() {
                this.thinkingContainer.classList.remove('hidden');
                this.thinkingContainer.classList.add('visible');
            }
            
            // 隐藏思维容器
            hideThinking() {
                this.thinkingContainer.classList.remove('visible');
                this.thinkingContainer.classList.add('hidden');
            }
            
            // 重置管道状态
            resetPipeline() {
                const stages = this.thinkingContainer.querySelectorAll('.pipeline-stage');
                stages.forEach(stage => {
                    stage.classList.remove('active', 'completed');
                    stage.querySelector('.stage-status').textContent = '待处理';
                });
                
                // 清空思考流
                const streamContent = document.getElementById('thinking-stream-content');
                streamContent.innerHTML = '<div class="stream-message idle">AI开始思考...</div>';
            }
            
            // 开始思考序列
            async startThinkingSequence() {
                // 激活输入阶段
                this.activateStage('input', '解析中');
                await this.delay(800);
                this.completeStage('input', '已完成');
                
                // 分析阶段
                this.activateStage('analysis', '分析中');
                await this.simulateThinkingProcess('project_analysis');
                this.completeStage('analysis', '已完成');
                
                // 推理阶段
                this.activateStage('reasoning', '推理中');
                await this.simulateThinkingProcess('mcp_integration');
                this.completeStage('reasoning', '已完成');
                
                // 创造阶段
                this.activateStage('creation', '生成中');
                await this.simulateThinkingProcess('ai_enhancement');
                this.completeStage('creation', '已完成');
                
                // 最终完成
                this.addThoughtToStream('🎉 开发计划生成完成！正在渲染最终结果...', 'synthesizing');
                
                // 3秒后自动收起
                setTimeout(() => {
                    const content = this.thinkingContainer.querySelector('.thinking-content');
                    content.classList.add('collapsed');
                    this.thinkingContainer.querySelector('.thinking-toggle').textContent = '📌';
                }, 3000);
            }
            
            // 激活管道阶段
            activateStage(stageName, status) {
                const stage = this.thinkingContainer.querySelector(`[data-stage="${stageName}"]`);
                if (stage) {
                    stage.classList.add('active');
                    stage.querySelector('.stage-status').textContent = status;
                }
            }
            
            // 完成管道阶段
            completeStage(stageName, status) {
                const stage = this.thinkingContainer.querySelector(`[data-stage="${stageName}"]`);
                if (stage) {
                    stage.classList.remove('active');
                    stage.classList.add('completed');
                    stage.querySelector('.stage-status').textContent = status;
                }
            }
            
            // 模拟思考过程
            async simulateThinkingProcess(patternType) {
                const pattern = this.thinkingPatterns[patternType];
                if (!pattern) return;
                
                for (const step of pattern) {
                    await this.addThoughtToStream(step.thought, step.mode);
                    await this.delay(1200 + Math.random() * 800); // 随机延迟增加真实感
                }
                
                // 添加一些视觉元素
                const randomElement = Object.values(this.visualElements)[
                    Math.floor(Math.random() * Object.keys(this.visualElements).length)
                ];
                await this.addThoughtToStream(randomElement, 'analyzing');
                await this.delay(600);
            }
            
            // 添加思考到流中
            async addThoughtToStream(thought, mode) {
                const streamContent = document.getElementById('thinking-stream-content');
                const modeConfig = this.thinkingModes[mode] || this.thinkingModes['analyzing'];
                
                // 移除空闲状态
                const idleMessage = streamContent.querySelector('.stream-message.idle');
                if (idleMessage) idleMessage.remove();
                
                const messageElement = document.createElement('div');
                messageElement.className = `stream-message ${modeConfig.style}`;
                messageElement.innerHTML = `
                    <div class="message-icon">${modeConfig.icon}</div>
                    <div class="message-content">
                        <div class="message-type">${modeConfig.title}</div>
                        <div class="message-text"></div>
                    </div>
                    <div class="message-timestamp">${new Date().toLocaleTimeString()}</div>
                `;
                
                streamContent.appendChild(messageElement);
                
                // 打字机效果
                const textElement = messageElement.querySelector('.message-text');
                await this.typewriterEffect(textElement, thought);
                
                // 滚动到底部
                streamContent.scrollTop = streamContent.scrollHeight;
                
                // 更新指标
                this.updateMetrics();
            }
            
            // 打字机效果
            async typewriterEffect(element, text) {
                element.textContent = '';
                for (let i = 0; i < text.length; i++) {
                    element.textContent += text.charAt(i);
                    await this.delay(this.thinkingSpeed);
                }
            }
            
            // 更新指标
            updateMetrics() {
                // 处理速度
                const speed = (15 + Math.random() * 25).toFixed(1);
                document.getElementById('processing-speed').textContent = `${speed} tok/s`;
                
                // 思考深度
                const depth = Math.min(100, (this.currentThoughts.length * 15) + Math.random() * 30);
                const depthBar = document.getElementById('thinking-depth');
                depthBar.style.width = `${depth}%`;
                
                // 创新指数
                const innovation = (75 + Math.random() * 20).toFixed(1);
                document.getElementById('innovation-score').textContent = `${innovation}%`;
            }
            
            // 延迟函数
            delay(ms) {
                return new Promise(resolve => setTimeout(resolve, ms));
            }
            
            // 获取当前思考状态
            getCurrentThinkingState() {
                return {
                    isActive: this.isActive,
                    thoughtCount: this.currentThoughts.length,
                    currentMode: this.currentMode
                };
            }
        }
        
        function switchTheme(themeName) {
            const body = document.body;
            const currentTheme = body.getAttribute('data-theme');
            
            if (currentTheme !== themeName) {
                // 添加切换动画类
                body.classList.add('theme-switching');
                
                // 设置新主题
                body.setAttribute('data-theme', themeName);
                
                // 显示主题切换提示
                showThemeNotification(themeName);
                
                // 更新主题指示器
                updateThemeIndicator();
                
                // 移除动画类
                setTimeout(() => {
                    body.classList.remove('theme-switching');
                }, 600);
                
                console.log(`🎨 Switched to ${themeName} theme`);
            }
        }
        
        function showThemeNotification(themeName) {
            const themeNames = {
                'tech': '🚀 科技创新',
                'health': '🌱 健康生活', 
                'finance': '💰 金融商业',
                'creative': '🎨 创意设计',
                'education': '🎓 教育学习',
                'lifestyle': '🏠 生活服务',
                'entertainment': '🎮 娱乐游戏',
                'security': '🔒 安全隐私',
                'default': '✨ 通用创新'
            };
            
            const notification = document.createElement('div');
            notification.className = 'theme-notification';
            notification.innerHTML = `
                <div class="theme-notification-content">
                    <span class="theme-icon">${themeNames[themeName].split(' ')[0]}</span>
                    <span class="theme-text">已切换至${themeNames[themeName].split(' ')[1]}主题</span>
                </div>
            `;
            
            document.body.appendChild(notification);
            
            // 动画显示
            setTimeout(() => notification.classList.add('show'), 100);
            
            // 自动隐藏
            setTimeout(() => {
                notification.classList.remove('show');
                setTimeout(() => document.body.removeChild(notification), 300);
            }, 2000);
        }
        
        // 智能主题切换绑定
        function bindIntelligentThemeDetection() {
            const ideaInput = document.querySelector('textarea[placeholder*="产品创意"]');
            const referenceInput = document.querySelector('input[placeholder*="参考链接"]');
            
            if (ideaInput) {
                let debounceTimer;
                ideaInput.addEventListener('input', function() {
                    clearTimeout(debounceTimer);
                    debounceTimer = setTimeout(() => {
                        const combinedText = this.value + ' ' + (referenceInput?.value || '');
                        const detectedTheme = detectThemeFromText(combinedText);
                        switchTheme(detectedTheme);
                    }, 1000); // 1秒防抖
                });
            }
        }
        
        // 🧠 智能提示系统 - 实时创意扩展建议
        class SmartSuggestionSystem {
            constructor() {
                this.suggestions = [];
                this.suggestionBox = null;
                this.isVisible = false;
                this.debounceTimer = null;
                this.currentInput = null;
                
                this.suggestionTemplates = {
                    'missing_target_audience': {
                        icon: '👥',
                        text: '建议添加目标用户群体描述',
                        suggestion: '，主要面向[年龄段/职业/兴趣群体]用户'
                    },
                    'missing_technology': {
                        icon: '⚙️',
                        text: '建议明确技术栈偏好',
                        suggestion: '，采用[React/Vue/原生/其他]技术架构'
                    },
                    'missing_scale': {
                        icon: '📏',
                        text: '建议说明项目规模',
                        suggestion: '，预期[个人项目/小团队/企业级]规模'
                    },
                    'missing_platform': {
                        icon: '📱',
                        text: '建议指定目标平台',
                        suggestion: '，支持[Web/移动端/桌面/全平台]'
                    },
                    'missing_business_model': {
                        icon: '💰',
                        text: '建议补充商业模式',
                        suggestion: '，通过[订阅/广告/交易佣金/一次性付费]盈利'
                    },
                    'missing_unique_value': {
                        icon: '✨',
                        text: '建议强调独特价值',
                        suggestion: '，与现有产品相比具有[具体优势]特色'
                    },
                    'missing_timeline': {
                        icon: '⏰',
                        text: '建议添加时间预期',
                        suggestion: '，计划在[3个月/半年/一年]内完成'
                    }
                };
            }
            
            init() {
                this.createSuggestionBox();
                this.bindInputListeners();
            }
            
            createSuggestionBox() {
                this.suggestionBox = document.createElement('div');
                this.suggestionBox.className = 'smart-suggestions';
                this.suggestionBox.style.cssText = `
                    position: absolute;
                    top: 100%;
                    left: 0;
                    right: 0;
                    background: var(--bg-primary);
                    backdrop-filter: blur(20px);
                    border-radius: 1rem;
                    box-shadow: var(--card-shadow);
                    border: 1px solid rgba(255,255,255,0.3);
                    margin-top: 0.5rem;
                    padding: 1rem;
                    z-index: 1000;
                    transform: translateY(-10px);
                    opacity: 0;
                    transition: all 0.3s ease;
                    display: none;
                `;
                
                const header = document.createElement('div');
                header.innerHTML = `
                    <div style="display: flex; align-items: center; margin-bottom: 0.75rem;">
                        <span style="font-size: 1.2rem; margin-right: 0.5rem;">🧠</span>
                        <span style="font-weight: 600; color: var(--text-primary);">智能建议</span>
                        <button id="close-suggestions" style="margin-left: auto; background: none; border: none; font-size: 1.2rem; cursor: pointer; opacity: 0.7;">×</button>
                    </div>
                `;
                
                this.suggestionBox.appendChild(header);
                
                const suggestionsList = document.createElement('div');
                suggestionsList.id = 'suggestions-list';
                this.suggestionBox.appendChild(suggestionsList);
                
                // 绑定关闭按钮
                header.querySelector('#close-suggestions').addEventListener('click', () => {
                    this.hideSuggestions();
                });
            }
            
            bindInputListeners() {
                const ideaInput = document.querySelector('textarea[placeholder*="产品创意"]');
                if (!ideaInput) return;
                
                this.currentInput = ideaInput;
                
                // 确保input container有相对定位
                const container = ideaInput.closest('.gr-textbox') || ideaInput.parentElement;
                if (container) {
                    container.style.position = 'relative';
                    container.appendChild(this.suggestionBox);
                }
                
                ideaInput.addEventListener('input', (e) => {
                    clearTimeout(this.debounceTimer);
                    this.debounceTimer = setTimeout(() => {
                        this.analyzePending(e.target.value);
                    }, 1500); // 1.5秒延迟
                });
                
                ideaInput.addEventListener('focus', () => {
                    if (this.suggestions.length > 0) {
                        this.showSuggestions();
                    }
                });
                
                // 点击外部隐藏建议
                document.addEventListener('click', (e) => {
                    if (!this.suggestionBox.contains(e.target) && e.target !== ideaInput) {
                        this.hideSuggestions();
                    }
                });
            }
            
            analyzePending(text) {
                if (!text || text.length < 20) {
                    this.hideSuggestions();
                    return;
                }
                
                this.suggestions = [];
                
                // 分析缺失要素
                const analysis = {
                    hasTargetAudience: /(?:用户|客户|学生|开发者|设计师|企业|个人|家庭|老人|年轻人|专业人士)/.test(text),
                    hasTechnology: /(?:React|Vue|Angular|Node|Python|Java|移动端|Web|桌面|原生|H5|小程序|APP)/.test(text),
                    hasScale: /(?:个人|团队|企业|公司|小型|中型|大型|创业|商业)/.test(text),
                    hasPlatform: /(?:网页|移动|桌面|iOS|Android|微信|支付宝|浏览器|客户端)/.test(text),
                    hasBusinessModel: /(?:免费|付费|订阅|广告|佣金|会员|充值|商城|电商)/.test(text),
                    hasUniqueValue: /(?:独特|创新|首创|领先|特色|优势|差异化|竞争力)/.test(text),
                    hasTimeline: /(?:月|年|周|天|阶段|期|时间|计划|预期|目标)/.test(text)
                };
                
                // 根据分析结果生成建议
                if (!analysis.hasTargetAudience) this.suggestions.push('missing_target_audience');
                if (!analysis.hasTechnology) this.suggestions.push('missing_technology');
                if (!analysis.hasScale) this.suggestions.push('missing_scale');
                if (!analysis.hasPlatform) this.suggestions.push('missing_platform');
                if (!analysis.hasBusinessModel) this.suggestions.push('missing_business_model');
                if (!analysis.hasUniqueValue) this.suggestions.push('missing_unique_value');
                if (!analysis.hasTimeline) this.suggestions.push('missing_timeline');
                
                // 限制建议数量，优先显示最重要的
                this.suggestions = this.suggestions.slice(0, 3);
                
                if (this.suggestions.length > 0) {
                    this.renderSuggestions();
                    this.showSuggestions();
                } else {
                    this.hideSuggestions();
                }
            }
            
            renderSuggestions() {
                const suggestionsList = this.suggestionBox.querySelector('#suggestions-list');
                suggestionsList.innerHTML = '';
                
                this.suggestions.forEach((suggestionKey, index) => {
                    const template = this.suggestionTemplates[suggestionKey];
                    const suggestionItem = document.createElement('div');
                    suggestionItem.className = 'suggestion-item';
                    suggestionItem.style.cssText = `
                        display: flex;
                        align-items: center;
                        padding: 0.75rem;
                        margin-bottom: 0.5rem;
                        background: rgba(255,255,255,0.5);
                        border-radius: 0.75rem;
                        cursor: pointer;
                        transition: all 0.2s ease;
                        border: 2px solid transparent;
                    `;
                    
                    suggestionItem.innerHTML = `
                        <span style="font-size: 1.2rem; margin-right: 0.75rem;">${template.icon}</span>
                        <div style="flex: 1;">
                            <div style="color: var(--text-primary); font-weight: 500; margin-bottom: 0.25rem;">${template.text}</div>
                            <div style="color: var(--text-secondary); font-size: 0.85rem;">${template.suggestion}</div>
                        </div>
                        <span style="color: var(--text-secondary); font-size: 0.8rem;">点击应用</span>
                    `;
                    
                    // 悬停效果
                    suggestionItem.addEventListener('mouseenter', () => {
                        suggestionItem.style.background = 'rgba(79, 70, 229, 0.1)';
                        suggestionItem.style.borderColor = 'rgba(79, 70, 229, 0.3)';
                        suggestionItem.style.transform = 'translateY(-1px)';
                    });
                    
                    suggestionItem.addEventListener('mouseleave', () => {
                        suggestionItem.style.background = 'rgba(255,255,255,0.5)';
                        suggestionItem.style.borderColor = 'transparent';
                        suggestionItem.style.transform = 'translateY(0)';
                    });
                    
                    // 点击应用建议
                    suggestionItem.addEventListener('click', () => {
                        this.applySuggestion(template.suggestion);
                        this.hideSuggestions();
                    });
                    
                    suggestionsList.appendChild(suggestionItem);
                });
            }
            
            applySuggestion(suggestion) {
                if (!this.currentInput) return;
                
                const currentValue = this.currentInput.value;
                const cursorPosition = this.currentInput.selectionStart;
                
                // 在光标位置插入建议，或追加到末尾
                let newValue;
                if (cursorPosition === currentValue.length) {
                    newValue = currentValue + suggestion;
                } else {
                    newValue = currentValue.slice(0, cursorPosition) + suggestion + currentValue.slice(cursorPosition);
                }
                
                this.currentInput.value = newValue;
                this.currentInput.focus();
                
                // 触发input事件以便其他系统感知变化
                const event = new Event('input', { bubbles: true });
                this.currentInput.dispatchEvent(event);
                
                // 显示成功提示
                this.showAppliedNotification();
            }
            
            showAppliedNotification() {
                const notification = document.createElement('div');
                notification.style.cssText = `
                    position: fixed;
                    top: 2rem;
                    right: 2rem;
                    z-index: 10000;
                    background: #10b981;
                    color: white;
                    padding: 1rem 1.5rem;
                    border-radius: 0.75rem;
                    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
                    font-weight: 600;
                    animation: slideInRight 0.3s ease-out;
                `;
                notification.innerHTML = '✅ 智能建议已应用';
                
                document.body.appendChild(notification);
                setTimeout(() => document.body.removeChild(notification), 2000);
            }
            
            showSuggestions() {
                if (this.isVisible) return;
                this.isVisible = true;
                this.suggestionBox.style.display = 'block';
                setTimeout(() => {
                    this.suggestionBox.style.opacity = '1';
                    this.suggestionBox.style.transform = 'translateY(0)';
                }, 10);
            }
            
            hideSuggestions() {
                if (!this.isVisible) return;
                this.isVisible = false;
                this.suggestionBox.style.opacity = '0';
                this.suggestionBox.style.transform = 'translateY(-10px)';
                setTimeout(() => {
                    this.suggestionBox.style.display = 'none';
                }, 300);
            }
        }
        
        // 📝 渐进式表单系统 - 根据输入复杂度动态展开选项
        class ProgressiveFormSystem {
            constructor() {
                this.expansionLevel = 0; // 0: 基础, 1: 中级, 2: 高级
                this.additionalFields = [];
                this.isExpanded = false;
                this.analysisTimer = null;
                this.currentComplexity = 0;
                
                this.complexityThresholds = {
                    basic: 50,      // 基础阈值：50字符
                    intermediate: 150,  // 中级阈值：150字符
                    advanced: 300   // 高级阈值：300字符
                };
                
                this.advancedFields = [
                    {
                        id: 'target_users',
                        label: '🎯 目标用户群体',
                        placeholder: '详细描述主要用户群体，如：年龄、职业、兴趣等',
                        type: 'textarea',
                        level: 1
                    },
                    {
                        id: 'tech_preferences',
                        label: '⚙️ 技术偏好',
                        placeholder: '指定希望使用的技术栈，如：React、Vue、Python等',
                        type: 'text',
                        level: 1
                    },
                    {
                        id: 'project_scale',
                        label: '📏 项目规模',
                        placeholder: '项目规模和团队大小预期',
                        type: 'select',
                        options: ['个人项目', '小团队(2-5人)', '中型团队(6-15人)', '大型团队(15+人)', '企业级项目'],
                        level: 1
                    },
                    {
                        id: 'timeline',
                        label: '⏰ 开发时间',
                        placeholder: '预期开发时间',
                        type: 'select',
                        options: ['1个月内', '3个月内', '半年内', '1年内', '长期项目'],
                        level: 1
                    },
                    {
                        id: 'budget_range',
                        label: '💰 预算范围',
                        placeholder: '大概的预算范围或资源投入',
                        type: 'select',
                        options: ['个人项目', '小型预算(<10万)', '中型预算(10-50万)', '大型预算(50万+)', '企业级预算'],
                        level: 2
                    },
                    {
                        id: 'unique_features',
                        label: '✨ 独特功能',
                        placeholder: '描述产品的核心创新点和独特功能',
                        type: 'textarea',
                        level: 2
                    },
                    {
                        id: 'competitor_analysis',
                        label: '🏆 竞品分析',
                        placeholder: '已知的类似产品或竞争对手',
                        type: 'textarea',
                        level: 2
                    },
                    {
                        id: 'success_metrics',
                        label: '📊 成功指标',
                        placeholder: '如何衡量项目成功，如：用户数、收入等',
                        type: 'textarea',
                        level: 2
                    }
                ];
            }
            
            init() {
                this.bindInputAnalysis();
                this.createProgressiveContainer();
            }
            
            bindInputAnalysis() {
                const ideaInput = document.querySelector('textarea[placeholder*="产品创意"]');
                if (!ideaInput) return;
                
                ideaInput.addEventListener('input', (e) => {
                    clearTimeout(this.analysisTimer);
                    this.analysisTimer = setTimeout(() => {
                        this.analyzeComplexity(e.target.value);
                    }, 800); // 800ms延迟
                });
            }
            
            createProgressiveContainer() {
                const mainCanvas = document.querySelector('.main-creation-canvas');
                if (!mainCanvas) return;
                
                // 创建渐进式表单容器
                this.progressiveContainer = document.createElement('div');
                this.progressiveContainer.id = 'progressive-form-container';
                this.progressiveContainer.style.cssText = `
                    margin-top: 1.5rem;
                    opacity: 0;
                    transform: translateY(-20px);
                    transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
                    display: none;
                `;
                
                // 插入到参考链接输入框之后
                const referenceInput = document.querySelector('input[placeholder*="参考链接"]');
                if (referenceInput) {
                    const referenceContainer = referenceInput.closest('.gr-textbox') || referenceInput.parentElement;
                    referenceContainer.parentNode.insertBefore(this.progressiveContainer, referenceContainer.nextSibling);
                }
            }
            
            analyzeComplexity(text) {
                if (!text) {
                    this.currentComplexity = 0;
                    this.collapseForm();
                    return;
                }
                
                let complexity = 0;
                
                // 基础复杂度：字符数
                complexity += Math.min(text.length * 0.5, 100);
                
                // 关键词丰富度
                const keywordCategories = {
                    technical: ['技术', '开发', '编程', '架构', '数据库', '前端', '后端', 'API', '框架'],
                    business: ['商业', '盈利', '用户', '市场', '竞争', '优势', '价值', '收入', '成本'],
                    functional: ['功能', '特性', '模块', '系统', '平台', '工具', '服务', '应用'],
                    temporal: ['时间', '阶段', '计划', '期限', '目标', '里程碑', '版本', '迭代']
                };
                
                for (const [category, keywords] of Object.entries(keywordCategories)) {
                    const matches = keywords.filter(keyword => text.includes(keyword)).length;
                    complexity += matches * 10;
                }
                
                // 句子结构复杂度
                const sentences = text.split(/[。！？.!?]/).filter(s => s.trim().length > 0);
                complexity += sentences.length * 5;
                
                // 详细描述加分
                if (text.includes('包括') || text.includes('支持') || text.includes('提供')) complexity += 15;
                if (text.includes('用户可以') || text.includes('能够')) complexity += 10;
                if (/\d+/.test(text)) complexity += 10; // 包含数字
                
                this.currentComplexity = Math.min(complexity, 300);
                this.updateFormExpansion();
            }
            
            updateFormExpansion() {
                const { basic, intermediate, advanced } = this.complexityThresholds;
                let newLevel = 0;
                
                if (this.currentComplexity >= advanced) {
                    newLevel = 2;
                } else if (this.currentComplexity >= intermediate) {
                    newLevel = 1;
                } else if (this.currentComplexity >= basic) {
                    newLevel = 1;
                }
                
                if (newLevel !== this.expansionLevel) {
                    this.expansionLevel = newLevel;
                    this.renderProgressiveForm();
                }
            }
            
            renderProgressiveForm() {
                if (this.expansionLevel === 0) {
                    this.collapseForm();
                    return;
                }
                
                // 显示进度指示器
                this.showExpansionIndicator();
                
                // 筛选要显示的字段
                const fieldsToShow = this.advancedFields.filter(field => field.level <= this.expansionLevel);
                
                // 生成表单HTML
                let formHTML = `
                    <div style="background: var(--bg-primary); backdrop-filter: blur(20px); border-radius: 1.5rem; padding: 2rem; border: 1px solid rgba(255,255,255,0.3); box-shadow: var(--card-shadow);">
                        <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
                            <span style="font-size: 1.3rem; margin-right: 0.75rem;">📝</span>
                            <h3 style="color: var(--text-primary); margin: 0; font-weight: 600;">智能表单展开</h3>
                            <span style="margin-left: auto; font-size: 0.85rem; color: var(--text-secondary); background: rgba(79, 70, 229, 0.1); padding: 0.25rem 0.75rem; border-radius: 1rem;">
                                ${this.expansionLevel === 1 ? '中级模式' : '高级模式'}
                            </span>
                        </div>
                        <p style="color: var(--text-secondary); margin-bottom: 1.5rem; font-size: 0.9rem;">
                            根据您的创意复杂度，我们为您提供了额外的选项来完善您的需求描述
                        </p>
                `;
                
                // 生成字段
                fieldsToShow.forEach((field, index) => {
                    formHTML += this.generateFieldHTML(field, index);
                });
                
                formHTML += `
                        <div style="margin-top: 1.5rem; text-align: center;">
                            <button id="collapse-form" style="background: rgba(107, 114, 128, 0.1); color: var(--text-secondary); border: none; padding: 0.5rem 1rem; border-radius: 0.75rem; cursor: pointer; font-size: 0.85rem;">
                                收起选项
                            </button>
                        </div>
                    </div>
                `;
                
                this.progressiveContainer.innerHTML = formHTML;
                this.expandForm();
                this.bindFieldEvents();
            }
            
            generateFieldHTML(field, index) {
                const animationDelay = index * 0.1;
                
                if (field.type === 'textarea') {
                    return `
                        <div style="margin-bottom: 1.25rem; animation: fadeInUp 0.4s ease-out ${animationDelay}s both;">
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 500; color: var(--text-primary);">${field.label}</label>
                            <textarea id="${field.id}" placeholder="${field.placeholder}" style="width: 100%; min-height: 80px; padding: 0.75rem; border: 2px solid rgba(79, 70, 229, 0.2); border-radius: 0.75rem; background: rgba(255, 255, 255, 0.9); resize: vertical; font-family: inherit;"></textarea>
                        </div>
                    `;
                } else if (field.type === 'select') {
                    const options = field.options.map(option => `<option value="${option}">${option}</option>`).join('');
                    return `
                        <div style="margin-bottom: 1.25rem; animation: fadeInUp 0.4s ease-out ${animationDelay}s both;">
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 500; color: var(--text-primary);">${field.label}</label>
                            <select id="${field.id}" style="width: 100%; padding: 0.75rem; border: 2px solid rgba(79, 70, 229, 0.2); border-radius: 0.75rem; background: rgba(255, 255, 255, 0.9); font-family: inherit;">
                                <option value="">请选择...</option>
                                ${options}
                            </select>
                        </div>
                    `;
                } else {
                    return `
                        <div style="margin-bottom: 1.25rem; animation: fadeInUp 0.4s ease-out ${animationDelay}s both;">
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 500; color: var(--text-primary);">${field.label}</label>
                            <input type="text" id="${field.id}" placeholder="${field.placeholder}" style="width: 100%; padding: 0.75rem; border: 2px solid rgba(79, 70, 229, 0.2); border-radius: 0.75rem; background: rgba(255, 255, 255, 0.9); font-family: inherit;">
                        </div>
                    `;
                }
            }
            
            bindFieldEvents() {
                // 绑定收起按钮
                const collapseBtn = document.getElementById('collapse-form');
                if (collapseBtn) {
                    collapseBtn.addEventListener('click', () => {
                        this.collapseForm();
                    });
                }
                
                // 绑定字段变化事件，自动更新主输入框
                this.advancedFields.forEach(field => {
                    const element = document.getElementById(field.id);
                    if (element) {
                        element.addEventListener('change', () => {
                            this.updateMainInput();
                        });
                    }
                });
            }
            
            updateMainInput() {
                const mainInput = document.querySelector('textarea[placeholder*="产品创意"]');
                if (!mainInput) return;
                
                let additionalInfo = [];
                
                this.advancedFields.forEach(field => {
                    const element = document.getElementById(field.id);
                    if (element && element.value.trim()) {
                        additionalInfo.push(`${field.label}: ${element.value}`);
                    }
                });
                
                if (additionalInfo.length > 0) {
                    // 在主输入框末尾添加补充信息（如果还没有的话）
                    const currentValue = mainInput.value;
                    const supplementText = `\\n\\n补充信息：\\n${additionalInfo.join('\\n')}`;
                    
                    if (!currentValue.includes('补充信息：')) {
                        mainInput.value = currentValue + supplementText;
                        
                        // 触发input事件
                        const event = new Event('input', { bubbles: true });
                        mainInput.dispatchEvent(event);
                    }
                }
            }
            
            showExpansionIndicator() {
                // 显示一个简短的展开提示
                if (!this.hasShownIndicator) {
                    const indicator = document.createElement('div');
                    indicator.style.cssText = `
                        position: fixed;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                        z-index: 10000;
                        background: var(--bg-primary);
                        backdrop-filter: blur(20px);
                        color: var(--text-primary);
                        padding: 1rem 2rem;
                        border-radius: 1rem;
                        box-shadow: var(--card-shadow);
                        border: 1px solid rgba(255,255,255,0.3);
                        animation: fadeInScale 0.4s ease-out;
                    `;
                    indicator.innerHTML = '🎯 检测到详细描述，为您展开高级选项';
                    
                    document.body.appendChild(indicator);
                    setTimeout(() => document.body.removeChild(indicator), 2000);
                    this.hasShownIndicator = true;
                }
            }
            
            expandForm() {
                this.isExpanded = true;
                this.progressiveContainer.style.display = 'block';
                setTimeout(() => {
                    this.progressiveContainer.style.opacity = '1';
                    this.progressiveContainer.style.transform = 'translateY(0)';
                }, 10);
            }
            
            collapseForm() {
                if (!this.isExpanded) return;
                this.isExpanded = false;
                this.progressiveContainer.style.opacity = '0';
                this.progressiveContainer.style.transform = 'translateY(-20px)';
                setTimeout(() => {
                    this.progressiveContainer.style.display = 'none';
                }, 500);
            }
        }
        
        // ✨ 一键优化系统 - AI自动优化创意描述质量
        class AutoOptimizeSystem {
            constructor() {
                this.isAnalyzing = false;
                this.currentInput = null;
                this.optimizeButton = null;
                this.lastAnalysis = null;
                this.optimizationHistory = [];
                
                // 优化规则库
                this.optimizationRules = {
                    // 长度优化
                    'length_insufficient': {
                        threshold: 30,
                        priority: 'high',
                        type: 'expansion',
                        message: '描述过于简短，建议添加更多细节',
                        suggestions: [
                            '添加目标用户群体描述',
                            '说明核心功能和特色',
                            '补充使用场景说明',
                            '明确解决的痛点问题'
                        ]
                    },
                    
                    // 结构优化
                    'structure_missing': {
                        priority: 'medium',
                        type: 'structure',
                        message: '缺少结构化描述',
                        suggestions: [
                            '按照"问题-解决方案-价值"的结构组织',
                            '分段描述不同功能模块',
                            '使用列表突出关键特性'
                        ]
                    },
                    
                    // 技术细节
                    'tech_details_missing': {
                        priority: 'medium',
                        type: 'technical',
                        message: '建议添加技术相关信息',
                        suggestions: [
                            '指定目标平台（Web/移动/桌面）',
                            '提及技术栈偏好',
                            '说明数据处理需求',
                            '考虑集成第三方服务'
                        ]
                    },
                    
                    // 商业价值
                    'business_value_missing': {
                        priority: 'medium',
                        type: 'business',
                        message: '建议补充商业价值说明',
                        suggestions: [
                            '明确盈利模式',
                            '分析市场定位',
                            '描述竞争优势',
                            '预估用户规模'
                        ]
                    },
                    
                    // 用户体验
                    'ux_considerations_missing': {
                        priority: 'medium',
                        type: 'ux',
                        message: '建议关注用户体验要素',
                        suggestions: [
                            '描述核心用户旅程',
                            '考虑界面设计风格',
                            '说明交互方式',
                            '关注无障碍性需求'
                        ]
                    }
                };
                
                // 优化模板库
                this.optimizationTemplates = {
                    'problem_solution_value': {
                        name: '问题-解决方案-价值模板',
                        structure: `
🎯 **解决的问题**：[描述用户痛点和现有方案的不足]

💡 **解决方案**：[详细说明您的创意如何解决这个问题]

🚀 **核心价值**：[说明为用户带来的具体价值和优势]

👥 **目标用户**：[明确主要用户群体和使用场景]

⚙️ **技术实现**：[简述技术方案和实现路径]
                        `.trim()
                    },
                    
                    'feature_focused': {
                        name: '功能导向模板',
                        structure: `
🎯 **产品概述**：[一句话概括产品核心]

✨ **核心功能**：
- [主要功能1：具体描述]
- [主要功能2：具体描述]
- [主要功能3：具体描述]

🎨 **用户体验**：[描述界面设计和交互特色]

🔧 **技术特性**：[说明技术亮点和创新点]

📈 **商业价值**：[阐述市场前景和盈利潜力]
                        `.trim()
                    },
                    
                    'user_centric': {
                        name: '用户中心模板',
                        structure: `
👤 **目标用户**：[详细描述主要用户群体]

😣 **用户痛点**：[分析用户当前遇到的问题]

💡 **解决方案**：[说明如何为用户创造价值]

🎯 **使用场景**：[描述典型的使用环境和流程]

🎨 **产品体验**：[用户从接触到使用的完整体验]

🚀 **未来规划**：[产品迭代和功能扩展方向]
                        `.trim()
                    }
                };
                
                // AI优化提示词模板
                this.aiOptimizationPrompts = {
                    'expand_idea': `请帮我扩展和优化这个产品创意描述，使其更加完整和具有说服力。原始创意："{original_idea}"
                    
请从以下角度进行优化：
1. 补充缺失的重要信息
2. 改善表达的清晰度
3. 增加技术和商业可行性分析
4. 保持原有创意的核心特色

输出格式要求：
- 保持创意的原始精神
- 使用结构化的描述方式
- 添加具体的实现建议
- 控制在200-300字内`,
                    
                    'restructure': `请帮我重新组织这个产品创意的描述结构，使其更加清晰和专业。原始描述："{original_idea}"
                    
请按照以下结构重新组织：
1. 核心概念（一句话概括）
2. 解决的问题
3. 目标用户群体
4. 主要功能特性
5. 技术实现方向
6. 商业价值预期

要求：
- 保留所有原有信息
- 逻辑结构清晰
- 表达简洁有力`,
                    
                    'enhance_details': `请帮我为这个产品创意添加更多技术和实现细节，使其更具可操作性。创意描述："{original_idea}"
                    
请补充以下方面的详细信息：
1. 技术架构建议
2. 核心功能的实现方式
3. 数据存储和处理方案
4. 用户界面设计考虑
5. 可能的技术挑战和解决思路

输出要求：
- 技术建议具体可行
- 考虑现有技术生态
- 平衡复杂度和实用性`
                };
            }
            
            init() {
                this.createOptimizeButton();
                this.bindInputListeners();
                this.loadOptimizationHistory();
                console.log('✨ 一键优化系统已初始化');
            }
            
            createOptimizeButton() {
                // 找到创意输入框
                const ideaInput = document.querySelector('textarea[placeholder*="产品创意"]');
                if (!ideaInput) return;
                
                const inputContainer = ideaInput.closest('.gr-textbox') || ideaInput.parentElement;
                
                // 创建优化按钮容器
                const optimizeContainer = document.createElement('div');
                optimizeContainer.style.cssText = `
                    margin-top: 0.75rem;
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    flex-wrap: wrap;
                `;
                
                // 主优化按钮
                this.optimizeButton = document.createElement('button');
                this.optimizeButton.className = 'auto-optimize-btn';
                this.optimizeButton.style.cssText = `
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    padding: 0.6rem 1.2rem;
                    border-radius: 1.5rem;
                    font-size: 0.9rem;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
                `;
                this.optimizeButton.innerHTML = `
                    <span style="font-size: 1rem;">✨</span>
                    <span>智能优化</span>
                `;
                
                // 模板选择按钮
                const templateButton = document.createElement('button');
                templateButton.className = 'template-btn';
                templateButton.style.cssText = `
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    color: white;
                    border: none;
                    padding: 0.6rem 1.2rem;
                    border-radius: 1.5rem;
                    font-size: 0.9rem;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    box-shadow: 0 4px 12px rgba(240, 147, 251, 0.3);
                `;
                templateButton.innerHTML = `
                    <span style="font-size: 1rem;">📝</span>
                    <span>使用模板</span>
                `;
                
                // 分析按钮
                const analyzeButton = document.createElement('button');
                analyzeButton.className = 'analyze-btn';
                analyzeButton.style.cssText = `
                    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                    color: white;
                    border: none;
                    padding: 0.6rem 1.2rem;
                    border-radius: 1.5rem;
                    font-size: 0.9rem;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    box-shadow: 0 4px 12px rgba(79, 172, 254, 0.3);
                `;
                analyzeButton.innerHTML = `
                    <span style="font-size: 1rem;">🔍</span>
                    <span>智能分析</span>
                `;
                
                // 添加悬停效果
                [this.optimizeButton, templateButton, analyzeButton].forEach(btn => {
                    btn.addEventListener('mouseenter', () => {
                        btn.style.transform = 'translateY(-2px) scale(1.02)';
                        btn.style.boxShadow = btn.style.boxShadow.replace('0.3', '0.4');
                    });
                    
                    btn.addEventListener('mouseleave', () => {
                        btn.style.transform = 'translateY(0) scale(1)';
                        btn.style.boxShadow = btn.style.boxShadow.replace('0.4', '0.3');
                    });
                });
                
                optimizeContainer.appendChild(this.optimizeButton);
                optimizeContainer.appendChild(templateButton);
                optimizeContainer.appendChild(analyzeButton);
                
                // 插入到输入框后面
                inputContainer.parentNode.insertBefore(optimizeContainer, inputContainer.nextSibling);
                
                // 绑定事件
                this.optimizeButton.addEventListener('click', () => this.performOptimization());
                templateButton.addEventListener('click', () => this.showTemplateSelector());
                analyzeButton.addEventListener('click', () => this.performAnalysis());
                
                this.currentInput = ideaInput;
            }
            
            bindInputListeners() {
                if (!this.currentInput) return;
                
                let analysisTimer = null;
                
                this.currentInput.addEventListener('input', () => {
                    clearTimeout(analysisTimer);
                    analysisTimer = setTimeout(() => {
                        this.updateOptimizeButtonState();
                    }, 1000);
                });
                
                this.updateOptimizeButtonState();
            }
            
            updateOptimizeButtonState() {
                if (!this.optimizeButton || !this.currentInput) return;
                
                const text = this.currentInput.value.trim();
                const textLength = text.length;
                
                if (textLength < 10) {
                    this.optimizeButton.style.opacity = '0.5';
                    this.optimizeButton.style.cursor = 'not-allowed';
                    this.optimizeButton.innerHTML = `
                        <span style="font-size: 1rem;">💭</span>
                        <span>先输入创意</span>
                    `;
                } else if (textLength < 50) {
                    this.optimizeButton.style.opacity = '0.8';
                    this.optimizeButton.style.cursor = 'pointer';
                    this.optimizeButton.innerHTML = `
                        <span style="font-size: 1rem;">⚡</span>
                        <span>快速优化</span>
                    `;
                } else {
                    this.optimizeButton.style.opacity = '1';
                    this.optimizeButton.style.cursor = 'pointer';
                    this.optimizeButton.innerHTML = `
                        <span style="font-size: 1rem;">✨</span>
                        <span>智能优化</span>
                    `;
                }
            }
            
            performOptimization() {
                if (!this.currentInput || this.isAnalyzing) return;
                
                const originalText = this.currentInput.value.trim();
                if (originalText.length < 10) {
                    this.showMessage('请先输入至少10个字符的创意描述', 'warning');
                    return;
                }
                
                this.isAnalyzing = true;
                this.showOptimizationDialog(originalText);
            }
            
            showOptimizationDialog(originalText) {
                const dialog = document.createElement('div');
                dialog.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.5);
                    backdrop-filter: blur(10px);
                    z-index: 10000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    animation: fadeIn 0.3s ease-out;
                `;
                
                const dialogContent = document.createElement('div');
                dialogContent.style.cssText = `
                    background: var(--bg-primary);
                    backdrop-filter: blur(20px);
                    border-radius: 2rem;
                    padding: 2rem;
                    max-width: 800px;
                    max-height: 80vh;
                    overflow-y: auto;
                    box-shadow: var(--card-shadow);
                    border: 1px solid rgba(255,255,255,0.3);
                    position: relative;
                    animation: slideInUp 0.4s ease-out;
                `;
                
                // 分析原始文本
                const analysis = this.analyzeText(originalText);
                const optimizedVersions = this.generateOptimizedVersions(originalText, analysis);
                
                dialogContent.innerHTML = `
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2rem;">
                        <h2 style="color: var(--text-primary); margin: 0; display: flex; align-items: center; gap: 0.75rem;">
                            <span style="font-size: 1.5rem;">✨</span>
                            <span>智能优化建议</span>
                        </h2>
                        <button onclick="this.closest('.optimization-dialog').remove(); autoOptimizer.isAnalyzing = false;" 
                                style="background: none; border: none; font-size: 1.5rem; cursor: pointer; opacity: 0.7; color: var(--text-primary);">×</button>
                    </div>
                    
                    <div style="margin-bottom: 2rem;">
                        <h3 style="color: var(--text-primary); margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
                            <span>🔍</span>分析结果
                        </h3>
                        <div style="background: rgba(79, 70, 229, 0.1); border-radius: 1rem; padding: 1.5rem; border-left: 4px solid #4f46e5;">
                            ${this.renderAnalysisResults(analysis)}
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 2rem;">
                        <h3 style="color: var(--text-primary); margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
                            <span>💡</span>优化建议
                        </h3>
                        <div style="display: grid; gap: 1rem;">
                            ${optimizedVersions.map((version, index) => `
                                <div class="optimization-option" data-index="${index}" style="
                                    background: rgba(255,255,255,0.7);
                                    border-radius: 1rem;
                                    padding: 1.5rem;
                                    border: 2px solid transparent;
                                    cursor: pointer;
                                    transition: all 0.3s ease;
                                ">
                                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
                                        <h4 style="color: var(--text-primary); margin: 0; display: flex; align-items: center; gap: 0.5rem;">
                                            <span>${version.icon}</span>
                                            <span>${version.title}</span>
                                        </h4>
                                        <span style="background: var(--primary-gradient); color: white; padding: 0.25rem 0.75rem; border-radius: 1rem; font-size: 0.8rem;">
                                            ${version.type}
                                        </span>
                                    </div>
                                    <p style="color: var(--text-secondary); margin-bottom: 1rem; font-size: 0.9rem;">
                                        ${version.description}
                                    </p>
                                    <div style="background: #f8fafc; border-radius: 0.75rem; padding: 1rem; border-left: 3px solid #3b82f6;">
                                        <div style="color: #374151; line-height: 1.6; white-space: pre-line;">${version.optimizedText}</div>
                                    </div>
                                    <div style="margin-top: 1rem; text-align: right;">
                                        <button onclick="autoOptimizer.applyOptimization('${version.optimizedText.replace(/'/g, "\\'").replace(/\n/g, '\\n')}')" 
                                                style="background: var(--primary-gradient); color: white; border: none; padding: 0.5rem 1rem; border-radius: 0.75rem; cursor: pointer; font-weight: 600;">
                                            应用此优化
                                        </button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    
                    <div style="display: flex; gap: 1rem; justify-content: center; margin-top: 2rem;">
                        <button onclick="autoOptimizer.showCustomOptimization('${originalText.replace(/'/g, "\\'").replace(/\n/g, '\\n')}')" 
                                style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 1rem; cursor: pointer; font-weight: 600;">
                            🎨 自定义优化
                        </button>
                        <button onclick="this.closest('.optimization-dialog').remove(); autoOptimizer.isAnalyzing = false;" 
                                style="background: #6b7280; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 1rem; cursor: pointer; font-weight: 600;">
                            取消
                        </button>
                    </div>
                `;
                
                dialog.className = 'optimization-dialog';
                dialog.appendChild(dialogContent);
                document.body.appendChild(dialog);
                
                // 添加选项悬停效果
                setTimeout(() => {
                    const options = dialog.querySelectorAll('.optimization-option');
                    options.forEach(option => {
                        option.addEventListener('mouseenter', () => {
                            option.style.borderColor = '#4f46e5';
                            option.style.transform = 'translateY(-2px)';
                            option.style.boxShadow = '0 8px 25px rgba(79, 70, 229, 0.15)';
                        });
                        
                        option.addEventListener('mouseleave', () => {
                            option.style.borderColor = 'transparent';
                            option.style.transform = 'translateY(0)';
                            option.style.boxShadow = 'none';
                        });
                    });
                }, 100);
            }
            
            analyzeText(text) {
                const analysis = {
                    length: text.length,
                    wordCount: text.split(/\s+/).filter(word => word.length > 0).length,
                    sentences: text.split(/[.!?。！？]/).filter(s => s.trim().length > 0).length,
                    issues: [],
                    strengths: [],
                    score: 0
                };
                
                // 分析各个维度
                const checks = {
                    hasTargetUser: /(?:用户|客户|人群|对象)/.test(text),
                    hasProblemStatement: /(?:问题|痛点|困难|挑战|不足)/.test(text),
                    hasSolution: /(?:解决|实现|提供|支持|帮助)/.test(text),
                    hasTechInfo: /(?:技术|平台|系统|架构|开发)/.test(text),
                    hasBusinessValue: /(?:价值|收益|盈利|商业|市场)/.test(text),
                    hasFeatures: /(?:功能|特性|特色|模块)/.test(text)
                };
                
                // 计算得分
                let score = 0;
                if (analysis.length >= 50) score += 20;
                if (analysis.length >= 100) score += 20;
                if (analysis.sentences >= 3) score += 15;
                
                Object.values(checks).forEach(hasElement => {
                    if (hasElement) score += 10;
                });
                
                analysis.score = Math.min(score, 100);
                
                // 识别问题
                if (analysis.length < 50) {
                    analysis.issues.push({ type: 'length', message: '描述过于简短，建议扩展至50字以上' });
                }
                if (!checks.hasTargetUser) {
                    analysis.issues.push({ type: 'target_user', message: '缺少目标用户描述' });
                }
                if (!checks.hasProblemStatement) {
                    analysis.issues.push({ type: 'problem', message: '未明确说明要解决的问题' });
                }
                if (!checks.hasTechInfo) {
                    analysis.issues.push({ type: 'tech', message: '缺少技术实现相关信息' });
                }
                
                // 识别优点
                if (checks.hasSolution) {
                    analysis.strengths.push('明确了解决方案');
                }
                if (checks.hasFeatures) {
                    analysis.strengths.push('描述了核心功能');
                }
                if (analysis.length > 100) {
                    analysis.strengths.push('描述详细充分');
                }
                
                return analysis;
            }
            
            generateOptimizedVersions(originalText, analysis) {
                const versions = [];
                
                // 扩展版本
                if (analysis.length < 100) {
                    versions.push({
                        icon: '📈',
                        title: '内容扩展版',
                        type: '详细化',
                        description: '在保持原有创意的基础上，补充缺失的关键信息',
                        optimizedText: this.expandContent(originalText, analysis)
                    });
                }
                
                // 结构化版本
                versions.push({
                    icon: '🏗️',
                    title: '结构优化版',
                    type: '结构化',
                    description: '重新组织内容结构，使逻辑更清晰，表达更专业',
                    optimizedText: this.restructureContent(originalText)
                });
                
                // 专业化版本
                versions.push({
                    icon: '💼',
                    title: '商业专业版',
                    type: '商业化',
                    description: '从商业角度优化描述，突出市场价值和竞争优势',
                    optimizedText: this.professionalizeContent(originalText)
                });
                
                return versions;
            }
            
            expandContent(originalText, analysis) {
                let expanded = originalText;
                
                // 添加用户群体信息
                if (!analysis.issues.find(i => i.type === 'target_user')) {
                    expanded += '\n\n目标用户：主要面向[具体用户群体]，解决他们在[特定场景]中遇到的[具体需求]。';
                }
                
                // 添加技术信息
                if (!analysis.issues.find(i => i.type === 'tech')) {
                    expanded += '\n\n技术实现：计划采用[技术栈]开发，支持[平台类型]，确保[性能特性]。';
                }
                
                // 添加价值主张
                expanded += '\n\n核心价值：通过[核心功能]，为用户提供[具体价值]，相比现有方案具有[独特优势]。';
                
                return expanded;
            }
            
            restructureContent(originalText) {
                return `🎯 **核心概念**\n${originalText.split('。')[0]}。\n\n💡 **解决的问题**\n[基于原始描述推断的用户痛点]\n\n👥 **目标用户**\n[主要用户群体和使用场景]\n\n⭐ **核心功能**\n• [功能特性1]\n• [功能特性2]\n• [功能特性3]\n\n🔧 **技术方向**\n[建议的技术实现方案]\n\n💎 **商业价值**\n[市场前景和盈利潜力分析]`;
            }
            
            professionalizeContent(originalText) {
                return `**项目概述**\n${originalText}\n\n**市场定位**\n针对[目标市场]的[用户群体]，提供[核心价值定位]的解决方案。\n\n**竞争优势**\n• 差异化特色：[独特卖点]\n• 技术优势：[技术创新点]\n• 用户体验：[体验亮点]\n\n**商业模式**\n通过[盈利方式]实现收入，预期[发展阶段]达到[商业目标]。\n\n**实施路径**\n第一阶段：[MVP功能]\n第二阶段：[功能扩展]\n第三阶段：[规模化发展]`;
            }
            
            renderAnalysisResults(analysis) {
                return `
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
                        <div style="text-align: center;">
                            <div style="font-size: 2rem; font-weight: bold; color: ${analysis.score >= 70 ? '#10b981' : analysis.score >= 40 ? '#f59e0b' : '#ef4444'};">
                                ${analysis.score}
                            </div>
                            <div style="color: var(--text-secondary); font-size: 0.9rem;">综合得分</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 1.5rem; font-weight: bold; color: var(--text-primary);">
                                ${analysis.length}
                            </div>
                            <div style="color: var(--text-secondary); font-size: 0.9rem;">字符数</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 1.5rem; font-weight: bold; color: var(--text-primary);">
                                ${analysis.wordCount}
                            </div>
                            <div style="color: var(--text-secondary); font-size: 0.9rem;">词汇数</div>
                        </div>
                    </div>
                    
                    ${analysis.issues.length > 0 ? `
                        <div style="margin-bottom: 1rem;">
                            <h4 style="color: #dc2626; margin-bottom: 0.5rem;">🔴 待改进项：</h4>
                            <ul style="margin: 0; padding-left: 1.5rem; color: var(--text-secondary);">
                                ${analysis.issues.map(issue => `<li>${issue.message}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    
                    ${analysis.strengths.length > 0 ? `
                        <div>
                            <h4 style="color: #059669; margin-bottom: 0.5rem;">✅ 优点亮点：</h4>
                            <ul style="margin: 0; padding-left: 1.5rem; color: var(--text-secondary);">
                                ${analysis.strengths.map(strength => `<li>${strength}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                `;
            }
            
            applyOptimization(optimizedText) {
                if (!this.currentInput) return;
                
                this.currentInput.value = optimizedText.replace(/\\n/g, '\n');
                this.currentInput.focus();
                
                // 触发input事件
                const event = new Event('input', { bubbles: true });
                this.currentInput.dispatchEvent(event);
                
                // 关闭对话框
                const dialog = document.querySelector('.optimization-dialog');
                if (dialog) {
                    dialog.remove();
                }
                
                this.isAnalyzing = false;
                this.showMessage('✅ 优化已应用！您的创意描述已经更加完善', 'success');
                
                // 保存优化历史
                this.saveOptimizationHistory(optimizedText);
            }
            
            showCustomOptimization(originalText) {
                // 关闭当前对话框
                const currentDialog = document.querySelector('.optimization-dialog');
                if (currentDialog) {
                    currentDialog.remove();
                }
                
                // 创建自定义优化对话框
                const dialog = document.createElement('div');
                dialog.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.5);
                    backdrop-filter: blur(10px);
                    z-index: 10000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    animation: fadeIn 0.3s ease-out;
                `;
                
                dialog.innerHTML = `
                    <div style="
                        background: var(--bg-primary);
                        backdrop-filter: blur(20px);
                        border-radius: 2rem;
                        padding: 2rem;
                        max-width: 600px;
                        width: 90%;
                        box-shadow: var(--card-shadow);
                        border: 1px solid rgba(255,255,255,0.3);
                        animation: slideInUp 0.4s ease-out;
                    ">
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2rem;">
                            <h2 style="color: var(--text-primary); margin: 0; display: flex; align-items: center; gap: 0.75rem;">
                                <span style="font-size: 1.5rem;">🎨</span>
                                <span>自定义优化</span>
                            </h2>
                            <button onclick="this.closest('div').remove(); autoOptimizer.isAnalyzing = false;" 
                                    style="background: none; border: none; font-size: 1.5rem; cursor: pointer; opacity: 0.7; color: var(--text-primary);">×</button>
                        </div>
                        
                        <div style="margin-bottom: 1.5rem;">
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: var(--text-primary);">
                                选择优化方向：
                            </label>
                            <select id="optimization-direction" style="
                                width: 100%;
                                padding: 0.75rem;
                                border: 2px solid rgba(79, 70, 229, 0.2);
                                border-radius: 0.75rem;
                                background: rgba(255, 255, 255, 0.9);
                                font-family: inherit;
                            ">
                                <option value="expand">内容扩展 - 添加更多细节和信息</option>
                                <option value="restructure">结构重组 - 优化逻辑结构和表达</option>
                                <option value="enhance">深度增强 - 添加技术和商业细节</option>
                            </select>
                        </div>
                        
                        <div style="margin-bottom: 1.5rem;">
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: var(--text-primary);">
                                优化需求说明（可选）：
                            </label>
                            <textarea id="optimization-requirements" placeholder="请描述您希望重点优化的方面，比如：补充技术细节、强调商业价值、改善表达方式等..." style="
                                width: 100%;
                                min-height: 80px;
                                padding: 0.75rem;
                                border: 2px solid rgba(79, 70, 229, 0.2);
                                border-radius: 0.75rem;
                                background: rgba(255, 255, 255, 0.9);
                                resize: vertical;
                                font-family: inherit;
                            "></textarea>
                        </div>
                        
                        <div style="display: flex; gap: 1rem; justify-content: center;">
                            <button onclick="autoOptimizer.performCustomOptimization('${originalText.replace(/'/g, "\\'").replace(/\n/g, '\\n')}')" 
                                    style="background: var(--primary-gradient); color: white; border: none; padding: 0.75rem 2rem; border-radius: 1rem; cursor: pointer; font-weight: 600;">
                                🚀 开始优化
                            </button>
                            <button onclick="this.closest('div').remove(); autoOptimizer.isAnalyzing = false;" 
                                    style="background: #6b7280; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 1rem; cursor: pointer; font-weight: 600;">
                                取消
                            </button>
                        </div>
                    </div>
                `;
                
                document.body.appendChild(dialog);
            }
            
            performCustomOptimization(originalText) {
                const direction = document.getElementById('optimization-direction').value;
                const requirements = document.getElementById('optimization-requirements').value;
                
                // 模拟AI优化过程
                const optimizedText = this.generateCustomOptimization(originalText, direction, requirements);
                
                // 关闭对话框
                const dialog = document.querySelector('div[style*="position: fixed"]');
                if (dialog) {
                    dialog.remove();
                }
                
                // 应用优化结果
                this.applyOptimization(optimizedText);
            }
            
            generateCustomOptimization(originalText, direction, requirements) {
                // 根据方向生成优化版本
                let optimized = originalText;
                
                if (direction === 'expand') {
                    optimized = this.expandContent(originalText, { issues: [{ type: 'all' }] });
                } else if (direction === 'restructure') {
                    optimized = this.restructureContent(originalText);
                } else if (direction === 'enhance') {
                    optimized = this.professionalizeContent(originalText);
                }
                
                // 如果有特殊要求，进一步定制
                if (requirements.trim()) {
                    optimized += `\n\n[基于您的要求"${requirements}"进行的定制优化]`;
                }
                
                return optimized;
            }
            
            showTemplateSelector() {
                const templates = Object.entries(this.optimizationTemplates);
                
                const dialog = document.createElement('div');
                dialog.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.5);
                    backdrop-filter: blur(10px);
                    z-index: 10000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    animation: fadeIn 0.3s ease-out;
                `;
                
                dialog.innerHTML = `
                    <div style="
                        background: var(--bg-primary);
                        backdrop-filter: blur(20px);
                        border-radius: 2rem;
                        padding: 2rem;
                        max-width: 800px;
                        max-height: 80vh;
                        overflow-y: auto;
                        box-shadow: var(--card-shadow);
                        border: 1px solid rgba(255,255,255,0.3);
                        animation: slideInUp 0.4s ease-out;
                    ">
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2rem;">
                            <h2 style="color: var(--text-primary); margin: 0; display: flex; align-items: center; gap: 0.75rem;">
                                <span style="font-size: 1.5rem;">📝</span>
                                <span>选择创意模板</span>
                            </h2>
                            <button onclick="this.closest('div').remove()" 
                                    style="background: none; border: none; font-size: 1.5rem; cursor: pointer; opacity: 0.7; color: var(--text-primary);">×</button>
                        </div>
                        
                        <div style="display: grid; gap: 1.5rem;">
                            ${templates.map(([key, template]) => `
                                <div class="template-option" data-key="${key}" style="
                                    background: rgba(255,255,255,0.7);
                                    border-radius: 1rem;
                                    padding: 1.5rem;
                                    border: 2px solid transparent;
                                    cursor: pointer;
                                    transition: all 0.3s ease;
                                ">
                                    <h3 style="color: var(--text-primary); margin-bottom: 1rem;">${template.name}</h3>
                                    <div style="background: #f8fafc; border-radius: 0.75rem; padding: 1rem; border-left: 3px solid #3b82f6;">
                                        <pre style="white-space: pre-wrap; font-family: inherit; margin: 0; color: #374151; line-height: 1.6;">${template.structure}</pre>
                                    </div>
                                    <div style="margin-top: 1rem; text-align: right;">
                                        <button onclick="autoOptimizer.applyTemplate('${key}')" 
                                                style="background: var(--primary-gradient); color: white; border: none; padding: 0.5rem 1rem; border-radius: 0.75rem; cursor: pointer; font-weight: 600;">
                                            使用此模板
                                        </button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
                
                document.body.appendChild(dialog);
                
                // 添加悬停效果
                setTimeout(() => {
                    const options = dialog.querySelectorAll('.template-option');
                    options.forEach(option => {
                        option.addEventListener('mouseenter', () => {
                            option.style.borderColor = '#4f46e5';
                            option.style.transform = 'translateY(-2px)';
                            option.style.boxShadow = '0 8px 25px rgba(79, 70, 229, 0.15)';
                        });
                        
                        option.addEventListener('mouseleave', () => {
                            option.style.borderColor = 'transparent';
                            option.style.transform = 'translateY(0)';
                            option.style.boxShadow = 'none';
                        });
                    });
                }, 100);
            }
            
            applyTemplate(templateKey) {
                const template = this.optimizationTemplates[templateKey];
                if (!template || !this.currentInput) return;
                
                this.currentInput.value = template.structure;
                this.currentInput.focus();
                
                // 触发input事件
                const event = new Event('input', { bubbles: true });
                this.currentInput.dispatchEvent(event);
                
                // 关闭对话框
                const dialog = document.querySelector('div[style*="position: fixed"]');
                if (dialog) {
                    dialog.remove();
                }
                
                this.showMessage(`✅ 已应用"${template.name}"模板`, 'success');
            }
            
            performAnalysis() {
                if (!this.currentInput) return;
                
                const text = this.currentInput.value.trim();
                if (text.length < 10) {
                    this.showMessage('请先输入至少10个字符的创意描述', 'warning');
                    return;
                }
                
                const analysis = this.analyzeText(text);
                this.showAnalysisResults(analysis);
            }
            
            showAnalysisResults(analysis) {
                const dialog = document.createElement('div');
                dialog.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.5);
                    backdrop-filter: blur(10px);
                    z-index: 10000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    animation: fadeIn 0.3s ease-out;
                `;
                
                dialog.innerHTML = `
                    <div style="
                        background: var(--bg-primary);
                        backdrop-filter: blur(20px);
                        border-radius: 2rem;
                        padding: 2rem;
                        max-width: 600px;
                        width: 90%;
                        box-shadow: var(--card-shadow);
                        border: 1px solid rgba(255,255,255,0.3);
                        animation: slideInUp 0.4s ease-out;
                    ">
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2rem;">
                            <h2 style="color: var(--text-primary); margin: 0; display: flex; align-items: center; gap: 0.75rem;">
                                <span style="font-size: 1.5rem;">🔍</span>
                                <span>创意分析报告</span>
                            </h2>
                            <button onclick="this.closest('div').remove()" 
                                    style="background: none; border: none; font-size: 1.5rem; cursor: pointer; opacity: 0.7; color: var(--text-primary);">×</button>
                        </div>
                        
                        <div style="background: rgba(79, 70, 229, 0.1); border-radius: 1rem; padding: 1.5rem; border-left: 4px solid #4f46e5;">
                            ${this.renderAnalysisResults(analysis)}
                        </div>
                        
                        <div style="text-align: center; margin-top: 2rem;">
                            <button onclick="this.closest('div').remove()" 
                                    style="background: var(--primary-gradient); color: white; border: none; padding: 0.75rem 2rem; border-radius: 1rem; cursor: pointer; font-weight: 600;">
                                了解了
                            </button>
                        </div>
                    </div>
                `;
                
                document.body.appendChild(dialog);
            }
            
            showMessage(message, type = 'info') {
                const messageEl = document.createElement('div');
                messageEl.style.cssText = `
                    position: fixed;
                    top: 2rem;
                    right: 2rem;
                    z-index: 10000;
                    background: ${type === 'success' ? '#10b981' : type === 'warning' ? '#f59e0b' : '#3b82f6'};
                    color: white;
                    padding: 1rem 1.5rem;
                    border-radius: 1rem;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                    animation: slideInRight 0.4s ease-out;
                    max-width: 300px;
                `;
                
                messageEl.textContent = message;
                document.body.appendChild(messageEl);
                
                setTimeout(() => {
                    if (messageEl.parentElement) {
                        messageEl.remove();
                    }
                }, 4000);
            }
            
            saveOptimizationHistory(optimizedText) {
                try {
                    const history = JSON.parse(localStorage.getItem('vibedoc_optimization_history') || '[]');
                    history.unshift({
                        text: optimizedText,
                        timestamp: new Date().toISOString()
                    });
                    
                    // 只保留最近的10次优化记录
                    if (history.length > 10) {
                        history.splice(10);
                    }
                    
                    localStorage.setItem('vibedoc_optimization_history', JSON.stringify(history));
                } catch(e) {
                    console.warn('无法保存优化历史');
                }
            }
            
            loadOptimizationHistory() {
                try {
                    this.optimizationHistory = JSON.parse(localStorage.getItem('vibedoc_optimization_history') || '[]');
                } catch {
                    this.optimizationHistory = [];
                }
            }
        }
        
        // 🎊 个性化欢迎体验系统 - 时间/偏好驱动的动态界面
        class PersonalizedWelcomeSystem {
            constructor() {
                this.isActive = false;
                this.currentTimeOfDay = 'morning';
                this.welcomeContainer = null;
                this.userPreferences = this.loadUserPreferences();
                this.visitCount = this.getVisitCount();
                this.lastVisit = this.getLastVisit();
                
                // 时间段配置
                this.timeOfDayConfig = {
                    'early-morning': { // 5-8点
                        icon: '🌅',
                        greeting: '清晨好',
                        message: '新的一天，新的创意！让我们从一个绝妙的想法开始',
                        bgGradient: 'linear-gradient(135deg, #ffeaa7 0%, #fab1a0 50%, #fd79a8 100%)',
                        actionText: '开启创意之旅'
                    },
                    'morning': { // 8-12点
                        icon: '☀️',
                        greeting: '上午好',
                        message: '阳光明媚的上午是最适合思考和创新的时候',
                        bgGradient: 'linear-gradient(135deg, #74b9ff 0%, #0984e3 50%, #6c5ce7 100%)',
                        actionText: '激发无限灵感'
                    },
                    'afternoon': { // 12-17点
                        icon: '🌞',
                        greeting: '下午好',
                        message: '午后的阳光正好，让创意在这温暖的时光中绽放',
                        bgGradient: 'linear-gradient(135deg, #55efc4 0%, #00cec9 50%, #00b894 100%)',
                        actionText: '创造精彩项目'
                    },
                    'evening': { // 17-20点
                        icon: '🌆',
                        greeting: '傍晚好',
                        message: '黄昏时分，让我们一起将今天的灵感转化为明天的现实',
                        bgGradient: 'linear-gradient(135deg, #fd79a8 0%, #fdcb6e 50%, #e17055 100%)',
                        actionText: '实现今日灵感'
                    },
                    'night': { // 20-24点
                        icon: '🌙',
                        greeting: '晚上好',
                        message: '夜深人静，正是深度思考的绝佳时机',
                        bgGradient: 'linear-gradient(135deg, #6c5ce7 0%, #a29bfe 50%, #fd79a8 100%)',
                        actionText: '深度创意思考'
                    },
                    'late-night': { // 0-5点
                        icon: '✨',
                        greeting: '深夜好',
                        message: '夜猫子的创意时间！灵感往往在安静的夜晚迸发',
                        bgGradient: 'linear-gradient(135deg, #2d3436 0%, #636e72 50%, #74b9ff 100%)',
                        actionText: '夜间灵感创作'
                    }
                };
                
                // 特殊日期配置
                this.specialDates = this.getSpecialDateConfig();
                
                // 用户成就等级
                this.userLevel = this.calculateUserLevel();
                
                // 动机语句库
                this.motivationalMessages = [
                    '💡 每个伟大的产品都始于一个简单的想法',
                    '🚀 今天的创意可能就是明天的独角兽',
                    '🌟 创新不是偶然，而是不断思考的结果',
                    '⚡ 最好的时间是现在，最好的创意就在您心中',
                    '🎯 将想法变成现实，这就是创造者的使命',
                    '🔥 每次尝试都是向成功迈进的一步',
                    '💎 真正的价值来自于解决真实的问题',
                    '🌈 多元化的思维创造多彩的解决方案'
                ];
            }
            
            init() {
                this.updateTimeOfDay();
                this.createWelcomeExperience();
                this.bindInteractionEvents();
                this.startPeriodicUpdates();
            }
            
            updateTimeOfDay() {
                const now = new Date();
                const hour = now.getHours();
                
                if (hour >= 5 && hour < 8) {
                    this.currentTimeOfDay = 'early-morning';
                } else if (hour >= 8 && hour < 12) {
                    this.currentTimeOfDay = 'morning';
                } else if (hour >= 12 && hour < 17) {
                    this.currentTimeOfDay = 'afternoon';
                } else if (hour >= 17 && hour < 20) {
                    this.currentTimeOfDay = 'evening';
                } else if (hour >= 20 && hour < 24) {
                    this.currentTimeOfDay = 'night';
                } else {
                    this.currentTimeOfDay = 'late-night';
                }
            }
            
            createWelcomeExperience() {
                // 查找并增强现有的header
                const headerGradient = document.querySelector('.header-gradient');
                if (!headerGradient) return;
                
                const timeConfig = this.timeOfDayConfig[this.currentTimeOfDay];
                const specialDate = this.getTodaySpecialDate();
                const randomMotivation = this.motivationalMessages[Math.floor(Math.random() * this.motivationalMessages.length)];
                
                // 创建个性化欢迎内容
                const welcomeContent = document.createElement('div');
                welcomeContent.className = 'personalized-welcome';
                welcomeContent.style.cssText = `
                    background: ${timeConfig.bgGradient};
                    margin: -3rem -3rem 2rem -3rem;
                    padding: 2rem 3rem;
                    border-radius: 2rem 2rem 0 0;
                    position: relative;
                    overflow: hidden;
                    animation: welcomeSlideIn 1s cubic-bezier(0.4, 0, 0.2, 1);
                `;
                
                // 添加动态背景效果
                const backgroundAnimation = document.createElement('div');
                backgroundAnimation.style.cssText = `
                    position: absolute;
                    top: -50%;
                    left: -50%;
                    width: 200%;
                    height: 200%;
                    background: linear-gradient(45deg, transparent 40%, rgba(255,255,255,0.1) 50%, transparent 60%);
                    animation: welcomeShine 8s linear infinite;
                    pointer-events: none;
                `;
                welcomeContent.appendChild(backgroundAnimation);
                
                // 构建欢迎信息
                let welcomeHTML = `
                    <div style="position: relative; z-index: 2; text-align: center;">
                        <div style="display: flex; align-items: center; justify-content: center; margin-bottom: 1rem;">
                            <span style="font-size: 3rem; margin-right: 1rem; animation: welcomeIconBounce 2s ease-in-out infinite;">${timeConfig.icon}</span>
                            <div>
                                <h2 style="color: white; margin: 0; font-size: 2rem; font-weight: 800; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">
                                    ${timeConfig.greeting}！欢迎回到 VibeDoc
                                </h2>
                                <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0; font-size: 1.1rem; text-shadow: 0 1px 2px rgba(0,0,0,0.2);">
                                    ${timeConfig.message}
                                </p>
                            </div>
                        </div>
                `;
                
                // 添加特殊日期信息
                if (specialDate) {
                    welcomeHTML += `
                        <div style="background: rgba(255,255,255,0.2); border-radius: 1rem; padding: 1rem; margin: 1rem 0; backdrop-filter: blur(10px);">
                            <span style="font-size: 1.2rem;">${specialDate.icon}</span>
                            <span style="color: white; font-weight: 600; margin-left: 0.5rem;">${specialDate.message}</span>
                        </div>
                    `;
                }
                
                // 添加用户统计信息
                const daysSinceLastVisit = this.getDaysSinceLastVisit();
                let userStats = '';
                
                if (this.visitCount === 1) {
                    userStats = `
                        <div style="background: rgba(255,255,255,0.15); border-radius: 1rem; padding: 1rem; margin: 1rem 0;">
                            <span style="font-size: 1.2rem;">🎉</span>
                            <span style="color: white; font-weight: 600; margin-left: 0.5rem;">欢迎首次使用！让我们开始您的创意之旅</span>
                        </div>
                    `;
                } else if (daysSinceLastVisit > 7) {
                    userStats = `
                        <div style="background: rgba(255,255,255,0.15); border-radius: 1rem; padding: 1rem; margin: 1rem 0;">
                            <span style="font-size: 1.2rem;">🌟</span>
                            <span style="color: white; font-weight: 600; margin-left: 0.5rem;">欢迎回来！距离上次访问已有${daysSinceLastVisit}天</span>
                        </div>
                    `;
                } else {
                    userStats = `
                        <div style="background: rgba(255,255,255,0.15); border-radius: 1rem; padding: 1rem; margin: 1rem 0;">
                            <span style="font-size: 1.2rem;">🔥</span>
                            <span style="color: white; font-weight: 600; margin-left: 0.5rem;">连续使用第${this.visitCount}次，您的创造力正在不断提升！</span>
                        </div>
                    `;
                }
                
                welcomeHTML += userStats;
                
                // 添加动机信息
                welcomeHTML += `
                        <div style="margin: 1.5rem 0; font-style: italic;">
                            <p style="color: rgba(255,255,255,0.8); margin: 0; font-size: 1rem;">
                                ${randomMotivation}
                            </p>
                        </div>
                        
                        <button class="personalized-action-btn" style="
                            background: rgba(255,255,255,0.2);
                            border: 2px solid rgba(255,255,255,0.3);
                            color: white;
                            padding: 0.75rem 2rem;
                            border-radius: 2rem;
                            font-size: 1rem;
                            font-weight: 600;
                            cursor: pointer;
                            backdrop-filter: blur(10px);
                            transition: all 0.3s ease;
                            text-shadow: 0 1px 2px rgba(0,0,0,0.2);
                        " onmouseover="this.style.background='rgba(255,255,255,0.3)'; this.style.transform='translateY(-2px)'" 
                           onmouseout="this.style.background='rgba(255,255,255,0.2)'; this.style.transform='translateY(0)'">
                            ${timeConfig.actionText}
                        </button>
                    </div>
                `;
                
                welcomeContent.innerHTML = welcomeHTML;
                
                // 插入到header的开头
                headerGradient.insertBefore(welcomeContent, headerGradient.firstChild);
                
                // 添加CSS动画
                this.addWelcomeAnimations();
                
                // 绑定按钮事件
                const actionBtn = welcomeContent.querySelector('.personalized-action-btn');
                if (actionBtn) {
                    actionBtn.addEventListener('click', () => {
                        this.focusOnCreativityInput();
                        this.showMotivationalTip();
                    });
                }
                
                // 更新访问记录
                this.updateVisitRecord();
                
                console.log(`🎊 个性化欢迎体验已激活 - 时段: ${this.currentTimeOfDay}, 访问次数: ${this.visitCount}`);
            }
            
            addWelcomeAnimations() {
                const style = document.createElement('style');
                style.textContent = `
                    @keyframes welcomeSlideIn {
                        from {
                            opacity: 0;
                            transform: translateY(-20px);
                        }
                        to {
                            opacity: 1;
                            transform: translateY(0);
                        }
                    }
                    
                    @keyframes welcomeShine {
                        0% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
                        100% { transform: translateX(100%) translateY(100%) rotate(45deg); }
                    }
                    
                    @keyframes welcomeIconBounce {
                        0%, 20%, 50%, 80%, 100% {
                            transform: translateY(0);
                        }
                        40% {
                            transform: translateY(-10px);
                        }
                        60% {
                            transform: translateY(-5px);
                        }
                    }
                    
                    .personalized-welcome .personalized-action-btn:hover {
                        box-shadow: 0 8px 25px rgba(255,255,255,0.3) !important;
                    }
                `;
                document.head.appendChild(style);
            }
            
            focusOnCreativityInput() {
                const ideaInput = document.querySelector('textarea[placeholder*="产品创意"]');
                if (ideaInput) {
                    ideaInput.focus();
                    ideaInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
            
            showMotivationalTip() {
                const tip = document.createElement('div');
                tip.style.cssText = `
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    z-index: 10000;
                    background: var(--bg-primary);
                    backdrop-filter: blur(20px);
                    color: var(--text-primary);
                    padding: 2rem;
                    border-radius: 1.5rem;
                    box-shadow: var(--card-shadow);
                    border: 1px solid rgba(255,255,255,0.3);
                    text-align: center;
                    max-width: 400px;
                    animation: fadeInScale 0.4s ease-out;
                `;
                
                const tips = [
                    '💡 从小的问题开始，往往能发现大的机会',
                    '🎯 最好的产品解决的是创造者自己遇到的问题',
                    '🚀 不要害怕简单的想法，简单往往更有力量',
                    '💎 用户体验比技术复杂性更重要',
                    '🌟 每天进步一点点，一年后就是巨大的飞跃'
                ];
                
                const randomTip = tips[Math.floor(Math.random() * tips.length)];
                
                tip.innerHTML = `
                    <div style="font-size: 2rem; margin-bottom: 1rem;">💫</div>
                    <h3 style="color: var(--text-primary); margin-bottom: 1rem;">创意小贴士</h3>
                    <p style="color: var(--text-secondary); margin-bottom: 2rem; line-height: 1.6;">${randomTip}</p>
                    <button onclick="this.parentElement.remove()" style="
                        background: var(--primary-gradient);
                        color: white;
                        border: none;
                        padding: 0.75rem 1.5rem;
                        border-radius: 1rem;
                        cursor: pointer;
                        font-weight: 600;
                    ">好的，开始创作！</button>
                `;
                
                document.body.appendChild(tip);
                setTimeout(() => {
                    if (tip.parentElement) {
                        tip.remove();
                    }
                }, 8000);
            }
            
            getSpecialDateConfig() {
                const today = new Date();
                const month = today.getMonth() + 1;
                const date = today.getDate();
                
                return {
                    '1-1': { icon: '🎊', message: '新年快乐！新的一年，新的创意征程' },
                    '2-14': { icon: '💝', message: '情人节快乐！用创意表达爱意' },
                    '4-1': { icon: '😄', message: '愚人节快乐！创意也需要一点幽默' },
                    '5-1': { icon: '💪', message: '劳动节快乐！创造本身就是最美的劳动' },
                    '6-1': { icon: '🧒', message: '儿童节快乐！保持童真的创造力' },
                    '10-1': { icon: '🇨🇳', message: '国庆节快乐！为祖国贡献创新力量' },
                    '12-25': { icon: '🎄', message: '圣诞快乐！愿您的创意如礼物般精彩' }
                };
            }
            
            getTodaySpecialDate() {
                const today = new Date();
                const month = today.getMonth() + 1;
                const date = today.getDate();
                const key = `${month}-${date}`;
                return this.specialDates[key] || null;
            }
            
            loadUserPreferences() {
                try {
                    return JSON.parse(localStorage.getItem('vibedoc_user_preferences') || '{}');
                } catch {
                    return {};
                }
            }
            
            saveUserPreferences(preferences) {
                try {
                    localStorage.setItem('vibedoc_user_preferences', JSON.stringify(preferences));
                } catch(e) {
                    console.warn('无法保存用户偏好设置');
                }
            }
            
            getVisitCount() {
                try {
                    return parseInt(localStorage.getItem('vibedoc_visit_count') || '0');
                } catch {
                    return 0;
                }
            }
            
            getLastVisit() {
                try {
                    return localStorage.getItem('vibedoc_last_visit') || null;
                } catch {
                    return null;
                }
            }
            
            updateVisitRecord() {
                try {
                    const now = new Date().toISOString();
                    const currentCount = this.getVisitCount();
                    localStorage.setItem('vibedoc_visit_count', (currentCount + 1).toString());
                    localStorage.setItem('vibedoc_last_visit', now);
                } catch(e) {
                    console.warn('无法更新访问记录');
                }
            }
            
            getDaysSinceLastVisit() {
                if (!this.lastVisit) return 0;
                try {
                    const lastVisitDate = new Date(this.lastVisit);
                    const now = new Date();
                    const diffTime = Math.abs(now - lastVisitDate);
                    return Math.floor(diffTime / (1000 * 60 * 60 * 24));
                } catch {
                    return 0;
                }
            }
            
            calculateUserLevel() {
                const visitCount = this.visitCount;
                if (visitCount >= 50) return { level: 5, title: '创意大师', icon: '👑' };
                if (visitCount >= 25) return { level: 4, title: '创新专家', icon: '🏆' };
                if (visitCount >= 10) return { level: 3, title: '灵感探索者', icon: '🌟' };
                if (visitCount >= 5) return { level: 2, title: '创意学徒', icon: '⭐' };
                return { level: 1, title: '新手创造者', icon: '🌱' };
            }
            
            bindInteractionEvents() {
                // 监听用户活动，动态调整体验
                let idleTimer = null;
                let isIdle = false;
                
                const resetIdleTimer = () => {
                    if (idleTimer) clearTimeout(idleTimer);
                    if (isIdle) {
                        isIdle = false;
                        this.showReturnWelcome();
                    }
                    
                    idleTimer = setTimeout(() => {
                        isIdle = true;
                    }, 300000); // 5分钟无操作视为空闲
                };
                
                ['mousedown', 'keydown', 'scroll', 'touchstart'].forEach(event => {
                    document.addEventListener(event, resetIdleTimer, true);
                });
                
                resetIdleTimer();
            }
            
            showReturnWelcome() {
                const returnMessage = document.createElement('div');
                returnMessage.style.cssText = `
                    position: fixed;
                    bottom: 2rem;
                    right: 2rem;
                    z-index: 9999;
                    background: var(--bg-primary);
                    backdrop-filter: blur(20px);
                    border-radius: 1rem;
                    padding: 1rem 1.5rem;
                    box-shadow: var(--card-shadow);
                    border: 1px solid rgba(255,255,255,0.3);
                    animation: slideInRight 0.4s ease-out;
                `;
                
                returnMessage.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <span style="font-size: 1.5rem;">👋</span>
                        <div>
                            <div style="font-weight: 600; color: var(--text-primary);">欢迎回来！</div>
                            <div style="font-size: 0.85rem; color: var(--text-secondary);">继续您的创意探索吧</div>
                        </div>
                        <button onclick="this.parentElement.parentElement.remove()" 
                                style="background: none; border: none; font-size: 1.2rem; cursor: pointer; opacity: 0.7;">×</button>
                    </div>
                `;
                
                document.body.appendChild(returnMessage);
                setTimeout(() => {
                    if (returnMessage.parentElement) {
                        returnMessage.remove();
                    }
                }, 5000);
            }
            
            startPeriodicUpdates() {
                // 每10分钟检查一次时间段变化
                setInterval(() => {
                    const oldTimeOfDay = this.currentTimeOfDay;
                    this.updateTimeOfDay();
                    if (oldTimeOfDay !== this.currentTimeOfDay) {
                        this.showTimeTransitionNotification();
                    }
                }, 600000); // 10分钟
            }
            
            showTimeTransitionNotification() {
                const timeConfig = this.timeOfDayConfig[this.currentTimeOfDay];
                const notification = document.createElement('div');
                notification.style.cssText = `
                    position: fixed;
                    top: 2rem;
                    right: 2rem;
                    z-index: 10000;
                    background: ${timeConfig.bgGradient};
                    color: white;
                    padding: 1rem 1.5rem;
                    border-radius: 1rem;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                    animation: slideInRight 0.4s ease-out;
                `;
                
                notification.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <span style="font-size: 1.5rem;">${timeConfig.icon}</span>
                        <div>
                            <div style="font-weight: 600;">${timeConfig.greeting}！</div>
                            <div style="font-size: 0.85rem; opacity: 0.9;">时光荏苒，创意不停</div>
                        </div>
                    </div>
                `;
                
                document.body.appendChild(notification);
                setTimeout(() => {
                    if (notification.parentElement) {
                        notification.remove();
                    }
                }, 4000);
            }
        }
        
        // 🔍 创意探索模式 - 生成期间展示行业趋势和灵感
        class CreativeExplorationMode {
            constructor() {
                this.isActive = false;
                this.currentTheme = 'default';
                this.explorationContainer = null;
                this.slideInterval = null;
                this.currentSlide = 0;
                this.slides = [];
                
                // 根据主题的行业趋势和灵感内容
                this.contentDatabase = {
                    'default': {
                        trends: [
                            { title: '🚀 AI驱动开发', content: '2025年，71%的开发团队使用AI工具提升效率，代码生成速度提升3倍' },
                            { title: '🌐 无代码运动', content: '低代码/无代码平台市场预计2025年达到650亿美元，民主化软件开发' },
                            { title: '🔒 隐私优先设计', content: '隐私保护成为产品核心竞争力，90%用户更信任透明的数据使用政策' }
                        ],
                        insights: [
                            { title: '💡 成功产品的共同特征', content: '简单易用、解决真实问题、快速迭代、用户反馈驱动' },
                            { title: '🎯 MVP策略', content: '先解决核心问题，再完善功能。Instagram最初只是照片滤镜应用' },
                            { title: '📱 移动优先思维', content: '60%用户首次接触产品通过移动设备，响应式设计不再是选择而是必需' }
                        ],
                        cases: [
                            { title: '🔥 Notion的成功之路', content: '从个人笔记工具发展为协作平台，专注用户体验和灵活性' },
                            { title: '⚡ Vercel的开发者生态', content: '通过优化开发体验，成为前端开发者首选部署平台' },
                            { title: '🎨 Figma的协作革命', content: '将设计工具云端化，打破设计与开发的壁垒' }
                        ]
                    },
                    'tech': {
                        trends: [
                            { title: '🤖 AI原生应用', content: 'AI-Native产品成为主流，ChatGPT用户突破2亿，展现AI产品巨大潜力' },
                            { title: '🧬 量子计算商业化', content: '量子计算开始在金融建模、药物发现等领域显示实用价值' },
                            { title: '🌟 边缘计算崛起', content: '边缘AI处理减少延迟90%，为实时应用提供新可能' }
                        ],
                        insights: [
                            { title: '🔬 技术选型策略', content: '选择成熟稳定的技术栈，避免过度工程化，优先考虑团队技能匹配' },
                            { title: '📊 数据驱动决策', content: '收集用户行为数据，A/B测试验证假设，用数据指导产品迭代' },
                            { title: '🔧 DevOps文化', content: '自动化部署、持续集成，让团队专注创新而非重复工作' }
                        ],
                        cases: [
                            { title: '🚀 OpenAI的API策略', content: '通过API开放AI能力，建立开发者生态，实现技术价值最大化' },
                            { title: '⚡ Stripe的开发者体验', content: '极致的文档和开发工具，让支付集成变得简单' },
                            { title: '🔒 1Password的安全创新', content: '将复杂的安全技术包装成简单易用的产品' }
                        ]
                    },
                    'health': {
                        trends: [
                            { title: '🏥 远程医疗普及', content: '远程医疗市场预计2025年达到2960亿美元，慢性病管理成为重点' },
                            { title: '💊 个性化医疗', content: '基因检测和AI诊断，实现千人千面的精准治疗方案' },
                            { title: '🧘 心理健康关注', content: '心理健康应用用户增长300%，冥想和减压成为刚需' }
                        ],
                        insights: [
                            { title: '🎯 用户信任建立', content: '健康领域需要专业认证、透明的数据使用政策、用户隐私保护' },
                            { title: '📱 简化复杂医疗', content: '将复杂医疗概念简化为用户易懂的界面和交互' },
                            { title: '👨‍⚕️ 专业性平衡', content: '在保持医疗专业性的同时，提供用户友好的体验' }
                        ],
                        cases: [
                            { title: '💚 Keep的运动生态', content: '从健身工具发展为运动生活方式平台，用户超3亿' },
                            { title: '🩺 平安好医生模式', content: '线上线下结合，为用户提供全方位健康管理服务' },
                            { title: '🧠 Calm的冥想市场', content: '专注睡眠和冥想，成为心理健康领域独角兽' }
                        ]
                    },
                    'finance': {
                        trends: [
                            { title: '💳 数字支付革命', content: '移动支付交易额突破100万亿，CBDC央行数字货币进入实用阶段' },
                            { title: '🏦 开放银行', content: 'API开放银行服务，第三方金融创新蓬勃发展' },
                            { title: '📊 智能投顾', content: 'AI投资顾问管理资产超10万亿，个人理财智能化' }
                        ],
                        insights: [
                            { title: '🔐 安全性优先', content: '金融产品必须符合严格监管要求，安全性是第一考虑' },
                            { title: '💡 降低门槛', content: '将复杂金融产品平民化，让普通用户也能享受专业服务' },
                            { title: '🎯 场景化服务', content: '在用户日常消费场景中嵌入金融服务' }
                        ],
                        cases: [
                            { title: '🚀 蚂蚁金服生态', content: '从支付工具发展为金融科技平台，服务超12亿用户' },
                            { title: '💎 Robinhood的股票民主化', content: '零佣金交易，让年轻人开始投资股票' },
                            { title: '🏛️ Stripe的全球支付', content: '简化在线支付，支持190+国家和地区' }
                        ]
                    },
                    'creative': {
                        trends: [
                            { title: '🎨 AI创作工具', content: 'AI绘画、写作工具爆发，创作门槛大幅降低，人人都是创作者' },
                            { title: '🌐 虚拟创作空间', content: 'VR/AR创作环境，为艺术家提供无限想象空间' },
                            { title: '💰 创作者经济', content: '创作者经济规模达1040亿美元，IP价值日益凸显' }
                        ],
                        insights: [
                            { title: '🎭 创意与技术融合', content: '最好的创意工具是让技术隐形，让创作者专注创意本身' },
                            { title: '🤝 社区驱动增长', content: '创意平台成功关键在于建立活跃的创作者社区' },
                            { title: '💡 版权保护创新', content: 'NFT和区块链技术为数字创作提供新的保护和变现方式' }
                        ],
                        cases: [
                            { title: '🎵 抖音的创意算法', content: '通过算法推荐，让每个人的创意都有被发现的机会' },
                            { title: '🎨 Canva的设计民主化', content: '将专业设计工具简化，让普通用户也能做出精美设计' },
                            { title: '📸 Instagram的视觉故事', content: '通过滤镜和故事功能，重新定义了照片分享体验' }
                        ]
                    },
                    'education': {
                        trends: [
                            { title: '🎓 在线教育爆发', content: '在线教育市场规模达3500亿美元，个性化学习成为趋势' },
                            { title: '🎮 游戏化学习', content: '教育游戏市场增长200%，寓教于乐提升学习效果' },
                            { title: '🤖 AI助教普及', content: 'AI助教24小时在线答疑，个性化学习路径推荐' }
                        ],
                        insights: [
                            { title: '🧠 学习科学应用', content: '基于认知科学研究，设计符合大脑学习规律的产品' },
                            { title: '📊 数据驱动教学', content: '学习数据分析，为每个学生提供个性化学习建议' },
                            { title: '👥 协作学习价值', content: '社交学习效果显著，同伴互助是重要学习方式' }
                        ],
                        cases: [
                            { title: '📚 Khan Academy的免费教育', content: '通过免费优质内容，让全球learners受益' },
                            { title: '🇨🇳 作业帮的AI应用', content: '拍照搜题到智能辅导，AI技术重塑学习体验' },
                            { title: '🎯 Coursera的职业教育', content: '与顶级大学合作，提供职业技能培训' }
                        ]
                    }
                };
            }
            
            init() {
                this.setupModeDetection();
                this.createExplorationContainer();
            }
            
            setupModeDetection() {
                // 监听生成按钮点击
                document.addEventListener('click', (e) => {
                    if (e.target.classList.contains('generate-btn') || 
                        e.target.textContent.includes('开始创造')) {
                        this.startExplorationMode();
                    }
                });
                
                // 监听主题变化
                const observer = new MutationObserver((mutations) => {
                    mutations.forEach((mutation) => {
                        if (mutation.type === 'attributes' && mutation.attributeName === 'data-theme') {
                            this.currentTheme = document.body.getAttribute('data-theme') || 'default';
                            if (this.isActive) {
                                this.updateContent();
                            }
                        }
                    });
                });
                observer.observe(document.body, { attributes: true });
            }
            
            createExplorationContainer() {
                this.explorationContainer = document.createElement('div');
                this.explorationContainer.id = 'creative-exploration';
                this.explorationContainer.style.cssText = `
                    position: fixed;
                    top: 2rem;
                    right: 2rem;
                    width: 350px;
                    max-height: 70vh;
                    background: var(--bg-primary);
                    backdrop-filter: blur(20px);
                    border-radius: 1.5rem;
                    box-shadow: var(--card-shadow);
                    border: 1px solid rgba(255,255,255,0.3);
                    z-index: 9999;
                    transform: translateX(100%);
                    opacity: 0;
                    transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
                    overflow: hidden;
                    display: none;
                `;
                
                document.body.appendChild(this.explorationContainer);
            }
            
            startExplorationMode() {
                if (this.isActive) return;
                
                this.isActive = true;
                this.currentTheme = document.body.getAttribute('data-theme') || 'default';
                this.prepareSlides();
                this.showContainer();
                this.startSlideshow();
                
                // 监听结果变化，如果生成完成则停止探索模式
                this.setupResultMonitoring();
            }
            
            prepareSlides() {
                const themeContent = this.contentDatabase[this.currentTheme] || this.contentDatabase['default'];
                this.slides = [
                    ...themeContent.trends.map(item => ({ ...item, type: 'trend' })),
                    ...themeContent.insights.map(item => ({ ...item, type: 'insight' })),
                    ...themeContent.cases.map(item => ({ ...item, type: 'case' }))
                ];
                
                // 随机打乱顺序
                this.slides = this.slides.sort(() => Math.random() - 0.5);
                this.currentSlide = 0;
            }
            
            showContainer() {
                this.explorationContainer.style.display = 'block';
                setTimeout(() => {
                    this.explorationContainer.style.transform = 'translateX(0)';
                    this.explorationContainer.style.opacity = '1';
                }, 100);
            }
            
            hideContainer() {
                this.explorationContainer.style.transform = 'translateX(100%)';
                this.explorationContainer.style.opacity = '0';
                setTimeout(() => {
                    this.explorationContainer.style.display = 'none';
                }, 500);
            }
            
            startSlideshow() {
                this.renderCurrentSlide();
                this.slideInterval = setInterval(() => {
                    this.nextSlide();
                }, 4000); // 每4秒切换
            }
            
            stopSlideshow() {
                if (this.slideInterval) {
                    clearInterval(this.slideInterval);
                    this.slideInterval = null;
                }
            }
            
            nextSlide() {
                this.currentSlide = (this.currentSlide + 1) % this.slides.length;
                this.renderCurrentSlide();
            }
            
            renderCurrentSlide() {
                const slide = this.slides[this.currentSlide];
                if (!slide) return;
                
                const typeIcons = {
                    'trend': '📈',
                    'insight': '💡',
                    'case': '🏆'
                };
                
                const typeLabels = {
                    'trend': '行业趋势',
                    'insight': '成功洞察',
                    'case': '成功案例'
                };
                
                const themeNames = {
                    'default': '通用创新',
                    'tech': '科技创新',
                    'health': '健康生活',
                    'finance': '金融商业',
                    'creative': '创意设计',
                    'education': '教育学习'
                };
                
                this.explorationContainer.innerHTML = `
                    <div style="padding: 2rem;">
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem;">
                            <div style="display: flex; align-items: center;">
                                <span style="font-size: 1.5rem; margin-right: 0.75rem;">🔍</span>
                                <h3 style="color: var(--text-primary); margin: 0; font-weight: 600; font-size: 1.1rem;">创意探索</h3>
                            </div>
                            <button id="close-exploration" style="background: none; border: none; font-size: 1.3rem; cursor: pointer; opacity: 0.7; color: var(--text-primary);">×</button>
                        </div>
                        
                        <div style="background: rgba(255,255,255,0.5); border-radius: 1rem; padding: 1.5rem; margin-bottom: 1rem;">
                            <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                                <span style="font-size: 1.3rem; margin-right: 0.5rem;">${typeIcons[slide.type]}</span>
                                <span style="background: var(--primary-gradient); color: white; padding: 0.25rem 0.75rem; border-radius: 1rem; font-size: 0.8rem; font-weight: 600;">
                                    ${typeLabels[slide.type]}
                                </span>
                                <span style="margin-left: 0.5rem; font-size: 0.75rem; color: var(--text-secondary);">
                                    ${themeNames[this.currentTheme]}
                                </span>
                            </div>
                            <h4 style="color: var(--text-primary); margin: 0 0 0.75rem 0; font-weight: 600; line-height: 1.4;">
                                ${slide.title}
                            </h4>
                            <p style="color: var(--text-secondary); margin: 0; font-size: 0.9rem; line-height: 1.6;">
                                ${slide.content}
                            </p>
                        </div>
                        
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            <div style="display: flex; gap: 0.25rem;">
                                ${this.slides.map((_, index) => `
                                    <div style="width: 8px; height: 8px; border-radius: 50%; background: ${index === this.currentSlide ? 'var(--primary-color)' : 'rgba(0,0,0,0.2)'}; transition: all 0.3s ease;"></div>
                                `).join('')}
                            </div>
                            <div style="font-size: 0.8rem; color: var(--text-secondary);">
                                ${this.currentSlide + 1}/${this.slides.length}
                            </div>
                        </div>
                        
                        <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid rgba(0,0,0,0.1);">
                            <p style="font-size: 0.75rem; color: var(--text-secondary); margin: 0; text-align: center; font-style: italic;">
                                💡 AI生成期间为您提供相关行业洞察
                            </p>
                        </div>
                    </div>
                `;
                
                // 绑定关闭按钮
                const closeBtn = document.getElementById('close-exploration');
                if (closeBtn) {
                    closeBtn.addEventListener('click', () => {
                        this.stopExplorationMode();
                    });
                }
            }
            
            updateContent() {
                if (!this.isActive) return;
                this.prepareSlides();
                this.currentSlide = 0;
                this.renderCurrentSlide();
            }
            
            setupResultMonitoring() {
                const planResult = document.getElementById('plan_result');
                if (!planResult) return;
                
                const observer = new MutationObserver((mutations) => {
                    mutations.forEach((mutation) => {
                        if (mutation.type === 'childList') {
                            const hasContent = planResult.textContent.includes('开发计划') || 
                                             planResult.textContent.includes('技术方案') ||
                                             planResult.textContent.includes('生成完成');
                            
                            if (hasContent && !planResult.textContent.includes('AI正在生成')) {
                                setTimeout(() => {
                                    this.stopExplorationMode();
                                }, 2000); // 延迟2秒关闭，让用户看到最后一个洞察
                            }
                        }
                    });
                });
                
                observer.observe(planResult, { childList: true, subtree: true });
                this.resultObserver = observer;
            }
            
            stopExplorationMode() {
                if (!this.isActive) return;
                
                this.isActive = false;
                this.stopSlideshow();
                this.hideContainer();
                
                if (this.resultObserver) {
                    this.resultObserver.disconnect();
                    this.resultObserver = null;
                }
            }
        }
        
        // 全局创意探索模式实例
        let creativeExplorationMode = null;
        let personalizedWelcome = null;
        let autoOptimizer = null;
        let colorPsychologySystem = null;
        let aiThinkingVisualization = null;
        
        // 🎨 创建主题指示器
        function createThemeIndicator() {
            const indicator = document.createElement('div');
            indicator.id = 'theme-indicator';
            indicator.className = 'theme-indicator';
            indicator.innerHTML = '✨';
            indicator.title = '当前主题: 通用创新';
            
            // 点击切换到下一个主题（演示功能）
            indicator.addEventListener('click', function() {
                const themes = ['default', 'tech', 'health', 'finance', 'creative', 'education', 'lifestyle', 'entertainment', 'security'];
                const currentTheme = document.body.getAttribute('data-theme') || 'default';
                const currentIndex = themes.indexOf(currentTheme);
                const nextTheme = themes[(currentIndex + 1) % themes.length];
                switchTheme(nextTheme);
            });
            
            document.body.appendChild(indicator);
            
            // 监听主题变化，更新指示器
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'data-theme') {
                        updateThemeIndicator();
                    }
                });
            });
            observer.observe(document.body, { attributes: true });
        }
        
        // 🎨 更新主题指示器
        function updateThemeIndicator() {
            const indicator = document.getElementById('theme-indicator');
            if (!indicator) return;
            
            const themeInfo = {
                'default': { icon: '✨', name: '通用创新' },
                'tech': { icon: '🚀', name: '科技创新' },
                'health': { icon: '🌱', name: '健康生活' },
                'finance': { icon: '💰', name: '金融商业' },
                'creative': { icon: '🎨', name: '创意设计' },
                'education': { icon: '🎓', name: '教育学习' },
                'lifestyle': { icon: '🏠', name: '生活服务' },
                'entertainment': { icon: '🎮', name: '娱乐游戏' },
                'security': { icon: '🔒', name: '安全隐私' }
            };
            
            const currentTheme = document.body.getAttribute('data-theme') || 'default';
            const info = themeInfo[currentTheme];
            
            indicator.innerHTML = info.icon;
            indicator.title = `当前主题: ${info.name} (点击切换)`;
        }
        
        // 代码复制功能
        function copyCode(button) {
            const codeCard = button.closest('.code-card');
            const codeBlock = codeCard.querySelector('pre code') || codeCard.querySelector('code');
            const text = codeBlock ? codeBlock.textContent : '';
            
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text).then(() => {
                    button.textContent = '✅ 已复制!';
                    setTimeout(() => {
                        button.textContent = '📋 复制代码';
                    }, 2000);
                }).catch(err => {
                    console.error('复制失败:', err);
                    fallbackCopyText(text);
                });
            } else {
                fallbackCopyText(text);
            }
        }
        
        // 卡片动画增强
        function addCardAnimations() {
            const cards = document.querySelectorAll('.content-card, .mermaid-card, .code-card');
            
            const observer = new IntersectionObserver((entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                    }
                });
            }, {
                threshold: 0.1
            });
            
            cards.forEach((card) => {
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';
                card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
                observer.observe(card);
            });
        }
        
        // 绑定复制按钮事件 - 简化版
        function bindCopyButtons() {
            document.querySelectorAll('.individual-copy-btn').forEach(button => {
                button.addEventListener('click', function() {
                    const promptId = this.getAttribute('data-prompt-id');
                    const promptContent = this.getAttribute('data-prompt-content');
                    copyIndividualPrompt(promptId, promptContent);
                });
            });
        }
        
        // 页面加载完成后初始化 - 简化版
        document.addEventListener('DOMContentLoaded', function() {
            updateMermaidTheme();
            bindCopyButtons();
            bindBasicProgress(); // 使用简化的进度绑定
            observeBasicResults(); // 使用简化的结果监听
            addCardAnimations(); // 添加卡片动画
            bindIntelligentThemeDetection(); // 🎨 启用智能主题检测
            
            // 🎨 创建主题指示器
            createThemeIndicator();
            
            // 🧠 初始化智能提示系统
            smartSuggestionSystem = new SmartSuggestionSystem();
            smartSuggestionSystem.init();
            
            // 📝 初始化渐进式表单系统
            progressiveFormSystem = new ProgressiveFormSystem();
            progressiveFormSystem.init();
            
            // 🔍 初始化创意探索模式
            creativeExplorationMode = new CreativeExplorationMode();
            creativeExplorationMode.init();
            
            // 🎊 初始化个性化欢迎体验
            personalizedWelcome = new PersonalizedWelcomeSystem();
            personalizedWelcome.init();
            
            // ✨ 初始化一键优化系统
            autoOptimizer = new AutoOptimizeSystem();
            autoOptimizer.init();
            
            // 🎯 初始化色彩心理学应用系统
            colorPsychologySystem = new ColorPsychologySystem();
            colorPsychologySystem.init();
            
            // 🎭 初始化AI思维可视化系统
            aiThinkingVisualization = new AIThinkingVisualizationSystem();
            aiThinkingVisualization.init();
            
            console.log('✅ 页面初始化完成 - 完整UI/UX创新系统已激活');
            
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
                            addCardAnimations(); // 为新内容添加动画
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
    
    # 主创作区域 - 恢复单栏布局
    with gr.Column(elem_classes="main-creation-canvas"):
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
        
        # 快速提示（简化版）
        gr.HTML("""
        <div style="text-align: center; margin: 1rem 0;">
            <span style="color: #64748b; font-size: 0.9rem; font-style: italic;">
                💡 30-100秒获得专业方案 | 🔄 支持实时进度显示 | ✨ 一键下载完整文档
            </span>
        </div>
        """)
    
    # 结果显示区域 - 卡片化布局
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
    
    # 简化的生成处理函数 - 增强错误处理
    def simple_generate_plan(user_idea: str, reference_url: str):
        """简化的计划生成函数 - 移除复杂流式处理"""
        try:
            logger.info("🚀 开始简化模式生成")
            start_time = time.time()
            
            # 验证API配置
            if not API_KEY:
                error_msg = """
## ❌ 配置错误：未设置API密钥

### 🔧 解决方法：
1. **获取API密钥**：访问 [Silicon Flow](https://siliconflow.cn) 注册并获取API密钥
2. **配置环境变量**：`export SILICONFLOW_API_KEY=your_api_key_here`
3. **重启应用**：配置完成后重启应用即可使用

💡 提示：这是正常的配置步骤，配置完成后即可生成专业开发方案。
"""
                return error_msg, "", ""
            
            # 直接调用核心生成函数
            plan_text, prompts_text, temp_file = generate_development_plan(user_idea, reference_url)
            
            elapsed_time = time.time() - start_time
            logger.info(f"✅ 生成完成，耗时: {elapsed_time:.1f}秒")
            
            # 确保生成结果有效
            if not plan_text or plan_text.startswith("❌"):
                return plan_text, prompts_text, temp_file
            
            # 在生成结果前添加性能信息
            performance_info = f"""
<div style="background: #e8f5e8; border-radius: 8px; padding: 1rem; margin: 1rem 0; text-align: center;">
    ✅ <strong>生成完成！</strong> 耗时: {elapsed_time:.1f}秒 | 
    🤖 使用模型: Qwen2.5-72B-Instruct | 
    🔗 MCP服务: {len([s for s in config.get_enabled_mcp_services()])}个已启用
</div>

---

{plan_text}
"""
            
            return performance_info, prompts_text, temp_file
            
        except Exception as e:
            elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
            logger.error(f"❌ 生成失败 ({elapsed_time:.1f}秒): {str(e)}")
            
            error_response = f"""
## ❌ 生成过程出现错误

**错误信息**: {str(e)}

**调试信息**:
- 生成时间: {elapsed_time:.1f}秒
- 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### 🔧 可能的解决方案：
1. 检查网络连接
2. 确认API密钥配置正确
3. 稍后重试

如果问题持续存在，请联系技术支持。
"""
            return error_response, "", ""
    
    # 绑定事件 - 简化版本
    generate_btn.click(
        fn=simple_generate_plan,
        inputs=[idea_input, reference_url_input],
        outputs=[plan_output, prompts_for_copy, download_file],
        api_name="generate_plan"
    ).then(
        fn=lambda: gr.update(visible=True),
        outputs=[download_file]
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