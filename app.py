import gradio as gr
import requests
import os
import logging
import json
import tempfile
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlparse

# 导入模块化组件
from config import config
from mcp_manager import mcp_manager

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
    
    # 额外的URL验证 - 防止虚假链接
    if any(fake_domain in url.lower() for fake_domain in [
        "example.com", "test.com", "fake.com", "xxx.com", 
        "docs.deepwiki.org", "api.deepwiki.org"  # 确保不调用不存在的deepwiki链接
    ]):
        logger.warning(f"⚠️ 检测到可能的虚假链接: {url}")
        return f"""
## ⚠️ 链接验证提醒

**🔗 提供的链接**: {url}

**❌ 链接状态**: 检测到可能的虚假或测试链接

**💡 建议**: 
- 请提供真实可访问的链接
- 或者移除参考链接，使用纯AI生成模式
- AI将基于创意描述生成专业的开发方案

---
"""
    
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

# 注释掉豆包图像生成函数，专注核心功能
# def generate_concept_logo(user_idea: str) -> str:
#     """生成概念LOGO和架构图 - 已移除以提升速度"""
#     return ""
# 
# def generate_image_with_doubao(prompt: str, image_type: str, doubao_service) -> str:
#     """使用豆包MCP生成单个图像 - 已移除以提升速度"""
#     return ""

def generate_development_plan_with_progress(user_idea: str, reference_url: str = "", progress_callback=None) -> Tuple[str, str, str]:
    """
    基于用户创意生成完整的产品开发计划和对应的AI编程助手提示词，支持进度回调。
    
    Args:
        user_idea (str): 用户的产品创意描述
        reference_url (str): 可选的参考链接
        progress_callback: 进度回调函数
        
    Returns:
        Tuple[str, str, str]: 开发计划、AI编程提示词、临时文件路径
    """
    def update_progress(step: int, message: str, details: str = ""):
        if progress_callback:
            progress_callback(step, message, details)
    
    # 第1步：验证输入 (10%)
    update_progress(1, "🔍 验证输入信息", "检查创意描述和参考链接...")
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
    
    # 第2步：获取外部知识 (25%)
    update_progress(2, "🌐 获取外部知识", "从参考链接获取技术文档和最佳实践...")
    retrieved_knowledge = fetch_external_knowledge(reference_url)
    
    # 第3步：构建AI提示词 (35%)
    update_progress(3, "🧠 构建AI提示词", "准备技术分析和代码生成指令...")
    
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

📊 视觉化内容要求（强制执行）：
- **必须**在技术方案中包含系统架构图的Mermaid代码
- **必须**在开发计划中包含项目甘特图的Mermaid代码  
- **必须**在功能模块中包含业务流程图的Mermaid代码
- **可选**添加数据库ERD图、API交互图等其他图表
- Mermaid图表必须使用完整的代码块格式
- 图表语法必须严格符合Mermaid 10.x版本规范
- 每个图表都要有清晰的标题和说明

🎯 Mermaid图表格式要求（严格执行）：

**系统架构图示例：**
```mermaid
graph TB
    subgraph "前端层"
        A[React应用] --> B[用户界面]
    end
    subgraph "后端层"
        C[API服务] --> D[业务逻辑]
        D --> E[数据访问层]
    end
    subgraph "数据层"
        F[MySQL数据库] --> G[Redis缓存]
    end
    B --> C
    E --> F
    E --> G
```

**项目甘特图示例：**
```mermaid
gantt
    title 项目开发甘特图
    dateFormat YYYY-MM-DD
    section 需求分析
    需求调研        :a1, 2024-01-01, 5d
    需求文档        :a2, after a1, 3d
    section 系统设计
    架构设计        :b1, after a2, 7d
    数据库设计      :b2, after b1, 3d
    section 开发实施
    后端开发        :c1, after b2, 14d
    前端开发        :c2, after b2, 14d
    集成测试        :c3, after c1, 5d
    section 部署运维
    环境准备        :d1, after c3, 3d
    正式发布        :d2, after d1, 2d
```

**业务流程图示例：**
```mermaid
flowchart TD
    A[用户登录] --> B{验证身份}
    B -->|成功| C[进入主页面]
    B -->|失败| D[显示错误信息]
    C --> E[选择功能]
    E --> F[执行操作]
    F --> G{操作结果}
    G -->|成功| H[显示成功信息]
    G -->|失败| I[显示错误信息]
    H --> E
    I --> E
    D --> A
```

⚠️ Mermaid语法注意事项（重要）：
- 每个代码块必须以 ```mermaid 开头，``` 结尾
- 甘特图的日期格式必须为 YYYY-MM-DD
- 流程图节点名称避免使用特殊字符，中文用方括号包围
- 图表标题要简洁明确，使用title关键字
- 子图用subgraph定义，提高可读性
- 箭头和连接线要清晰，使用适当的箭头样式

🎯 图表质量要求：
- 系统架构图：体现完整的技术栈和组件关系
- 甘特图：包含详细的时间安排和依赖关系
- 流程图：展示清晰的业务逻辑和决策路径
- 所有图表都要与项目内容高度相关，不使用通用模板

🎯 AI编程提示词格式要求（重要）：
- 必须在开发计划后生成专门的"# AI编程助手提示词"部分
- 每个功能模块必须有一个专门的AI编程提示词
- 每个提示词必须使用```代码块格式，方便复制
- 提示词内容要基于具体项目功能，包含详细的技术规范
- 提示词要详细、具体、可直接用于AI编程工具
- 必须包含完整的上下文和具体要求
- 每个提示词都要包含实际的代码示例或结构

🔧 提示词结构要求（严格执行）：
每个提示词使用以下格式：

## [功能名称]开发提示词

```
# [具体项目名称] - [功能名称]模块开发

## 项目背景
[基于开发计划的项目背景，包含技术栈和架构信息]

## 功能需求
### 核心功能
1. [具体功能1] - 实现[详细描述]
2. [具体功能2] - 支持[详细描述]
3. [具体功能3] - 提供[详细描述]

### 技术要求
- 框架：[具体框架版本]
- 数据库：[具体数据库和设计]
- API：[具体接口规范]
- 性能：[具体性能指标]

### 代码结构
请按以下结构组织代码：
```
[目录结构示例]
src/
├── [模块名]/
│   ├── [文件1].js
│   ├── [文件2].js
│   └── index.js
```

## 实现要求
1. **代码规范**：遵循[具体编码规范]
2. **错误处理**：实现完整的try-catch和验证
3. **测试覆盖**：包含单元测试和集成测试
4. **文档说明**：添加详细的JSDoc注释
5. **性能优化**：[具体优化要求]

## 输出要求
请提供：
1. 完整的功能实现代码
2. 配置文件（如有需要）
3. 测试用例代码
4. 使用文档和示例
5. 部署脚本（如有需要）

## 验收标准
- [ ] 功能完整性：[具体标准]
- [ ] 代码质量：[具体标准]
- [ ] 性能指标：[具体标准]
- [ ] 测试覆盖率：>90%
```

重要：每个提示词都必须根据具体项目需求定制，包含项目名称、技术栈、具体功能要求等详细信息。避免使用通用模板。

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
2. 高质量的AI编程助手提示词，必须满足以下要求：
   - 每个功能模块对应一个详细的编程提示词
   - 包含具体的项目背景和技术栈信息
   - 提供详细的功能需求和技术规范
   - 包含代码结构和目录组织建议
   - 明确的验收标准和性能指标
   - 实际可用的代码示例或接口定义

确保提示词具体、专业、可操作，能直接用于AI编程工具生成高质量代码。"""

    try:
        # 第4步：调用AI API生成方案 (60%)
        update_progress(4, "🤖 AI分析生成中", "调用Qwen2.5-72B模型，生成完整技术方案...")
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
                "max_tokens": 8000,  # 增加到8000确保图表和提示词完整性
                "temperature": 0.5,  # 降低到0.5提高一致性和速度
                "top_p": 0.85,       # 优化top_p平衡质量和速度
                "frequency_penalty": 0.2,  # 增加到0.2减少重复
                "presence_penalty": 0.1    # 添加存在惩罚提高多样性
            },
            timeout=75  # 进一步减少到75秒
        )
        
        if response.status_code == 200:
            content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                # 第5步：格式化内容 (80%)
                update_progress(5, "📋 格式化内容", "美化显示效果，优化图表和提示词...")
                final_plan_text = format_response(content)
                
                # 第6步：生成完成 (95%)
                update_progress(6, "✅ 生成完成", "创建下载文件，准备展示结果...")
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

def generate_with_progress_ui(user_idea: str, reference_url: str = ""):
    """
    带进度显示的UI生成函数
    """
    import time
    from datetime import datetime
    
    progress_steps = [
        (1, "🔍 验证输入信息", "检查创意描述和参考链接...", ["输入验证", "格式检查", "内容分析"]),
        (2, "🌐 获取外部知识", "从参考链接获取技术文档和最佳实践...", ["链接验证", "内容抓取", "知识提取"]),
        (3, "🧠 构建AI提示词", "准备技术分析和代码生成指令...", ["提示词优化", "上下文构建", "参数配置"]),
        (4, "🤖 AI分析生成中", "调用Qwen2.5-72B模型，生成完整技术方案...", ["模型调用", "内容生成", "结构化处理"]),
        (5, "📋 格式化内容", "美化显示效果，优化图表和提示词...", ["内容美化", "图表渲染", "格式优化"]),
        (6, "✅ 生成完成", "创建下载文件，准备展示结果...", ["文件创建", "最终检查", "结果展示"])
    ]
    
    def create_progress_html(current_step, task_name, task_details, preview_items):
        progress_percentage = (current_step / 6) * 100
        
        # 生成步骤指示器
        steps_html = ""
        for i in range(1, 7):  # 改为6步
            if i < current_step:
                status_class = "completed"
                icon = "✅"
            elif i == current_step:
                status_class = "active"
                icon = str(i)
            else:
                status_class = "pending"
                icon = str(i)
                
            steps_html += f"""
            <div class="progress-step {status_class}">
                <div class="progress-step-circle">{icon}</div>
                <div class="progress-step-label">第{i}步</div>
            </div>
            """
        
        # 生成预览列表
        preview_html = ""
        for idx, item in enumerate(preview_items):
            if idx < len(preview_items) * (current_step - 1) / 6:  # 改为6步
                item_class = "completed"
                icon = "✅"
            elif idx == int(len(preview_items) * (current_step - 1) / 6):
                item_class = "current"
                icon = "🔄"
            else:
                item_class = "pending"
                icon = "⏳"
                
            preview_html += f"""
            <li class="progress-preview-item {item_class}">
                <span>{icon}</span> {item}
            </li>
            """
        
        return f"""
        <div class="progress-container" style="display: block;">
            <div class="progress-header">
                <div class="progress-title">🚀 AI正在为您生成专业开发方案</div>
                <div class="progress-subtitle">预计还需 {max(0, (7-current_step)*12)} 秒，请稍候...</div>
            </div>
            
            <div class="progress-bar-container">
                <div class="progress-bar" style="width: {progress_percentage}%"></div>
            </div>
            
            <div class="progress-steps">
                {steps_html}
            </div>
            
            <div class="progress-current-task">
                <div class="progress-task-name">{task_name}</div>
                <div class="progress-task-details">{task_details}</div>
            </div>
            
            <div class="progress-preview">
                <div class="progress-preview-title">🎯 生成内容预览</div>
                <ul class="progress-preview-list">
                    {preview_html}
                </ul>
            </div>
        </div>
        """
    
    # 生成器函数，逐步返回进度
    def progress_generator():
        for step, task_name, task_details, preview_items in progress_steps:
            # 创建进度HTML
            progress_html = create_progress_html(step, task_name, task_details, preview_items)
            
            # 模拟处理时间
            if step == 4:  # AI生成阶段较慢
                yield (progress_html, "", "", "")
                time.sleep(2)  # AI调用需要更多时间
            else:
                yield (progress_html, "", "", "")
                time.sleep(1)  # 其他步骤较快
        
        # 调用实际的生成函数
        plan_content, prompts_content, temp_file = generate_development_plan(user_idea, reference_url)
        
        # 隐藏进度条，显示结果
        yield ("", plan_content, prompts_content, temp_file)
    
    return progress_generator()

def generate_development_plan_gradio(user_idea: str, reference_url: str = ""):
    """
    Gradio兼容的生成函数
    """
    try:
        # 直接调用原始函数
        plan_content, prompts_content, temp_file = generate_development_plan_with_progress(user_idea, reference_url, None)
        # 返回结果时，进度容器应该为空（由JavaScript隐藏）
        return plan_content, prompts_content, temp_file, ""
    except Exception as e:
        error_msg = f"❌ 生成过程中出现错误: {str(e)}"
        return error_msg, "", "", ""

def generate_development_plan(user_idea: str, reference_url: str = "") -> Tuple[str, str, str]:
    """
    原始的开发计划生成函数，保持向后兼容性
    """
    return generate_development_plan_with_progress(user_idea, reference_url, None)

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
            enhanced_lines.append('# 🤖 AI编程提示词')
            enhanced_lines.append('')
            enhanced_lines.append('> 💡 **使用说明**：复制提示词到 Claude Code、GitHub Copilot、ChatGPT 等AI编程工具中使用')
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

# 自定义CSS - 优化的UI布局
custom_css = """
/* ========================
   🎨 主要布局优化
   ======================== */

.main-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}

.main-input-row {
    gap: 2rem !important;
    align-items: stretch !important;
    margin: 2rem 0 !important;
}

.input-column {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    padding: 2rem;
    border-radius: 1.5rem;
    box-shadow: 0 8px 25px rgba(59, 130, 246, 0.1);
    border: 1px solid #e2e8f0;
    min-height: 400px;
}

.dark .input-column {
    background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
    border-color: #374151;
}

.tips-column {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    padding: 1.5rem;
    border-radius: 1.5rem;
    border: 2px solid #e5e7eb;
    min-height: 400px;
}

.dark .tips-column {
    background: linear-gradient(135deg, #374151 0%, #1f2937 100%);
    border-color: #4b5563;
}

/* ========================
   📝 输入组件优化
   ======================== */

.input-group {
    background: rgba(255, 255, 255, 0.6) !important;
    border-radius: 1rem !important;
    padding: 1.5rem !important;
    margin: 1.5rem 0 !important;
    border: 2px solid rgba(59, 130, 246, 0.1) !important;
}

.dark .input-group {
    background: rgba(55, 65, 81, 0.6) !important;
    border-color: rgba(96, 165, 250, 0.2) !important;
}

.main-input textarea {
    min-height: 180px !important;
    font-size: 1rem !important;
    line-height: 1.6 !important;
    border-radius: 0.8rem !important;
    border: 2px solid #e5e7eb !important;
    padding: 1rem !important;
    transition: all 0.3s ease !important;
}

.main-input textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
}

.url-input textarea {
    min-height: 60px !important;
    font-size: 0.95rem !important;
    border-radius: 0.8rem !important;
    border: 2px solid #e5e7eb !important;
    padding: 0.8rem !important;
}

.url-input textarea:focus {
    border-color: #10b981 !important;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1) !important;
}

/* ========================
   🚀 按钮优化
   ======================== */

.generate-btn-enhanced {
    background: linear-gradient(45deg, #3b82f6, #1d4ed8) !important;
    border: none !important;
    color: white !important;
    padding: 1.2rem 3rem !important;
    border-radius: 2rem !important;
    font-weight: 700 !important;
    font-size: 1.2rem !important;
    transition: all 0.4s ease !important;
    box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4) !important;
    text-transform: none !important;
    letter-spacing: 0.5px !important;
    position: relative !important;
    overflow: hidden !important;
    margin: 2rem 0 1rem 0 !important;
    width: 100% !important;
}

.generate-btn-enhanced:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 12px 35px rgba(59, 130, 246, 0.5) !important;
    background: linear-gradient(45deg, #1d4ed8, #1e40af) !important;
}

.generate-btn-enhanced::before {
    content: "";
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    transition: left 0.5s;
}

.generate-btn-enhanced:hover::before {
    left: 100%;
}

/* ========================
   💡 提示区域重设计
   ======================== */

.tips-container {
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.tip-section {
    background: rgba(255, 255, 255, 0.8);
    border-radius: 1rem;
    padding: 1.5rem;
    border-left: 4px solid #3b82f6;
    transition: all 0.3s ease;
}

.tip-section:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(59, 130, 246, 0.15);
}

.tip-section.primary {
    border-left-color: #ef4444;
}

.tip-section.secondary {
    border-left-color: #10b981;
}

.dark .tip-section {
    background: rgba(55, 65, 81, 0.8);
    color: #f8fafc;
}

.tip-section h4 {
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 1rem;
    color: #1f2937;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.dark .tip-section h4 {
    color: #f8fafc;
}

.tip-items {
    display: flex;
    flex-direction: column;
    gap: 0.8rem;
}

.tip-item {
    font-size: 0.9rem;
    color: #4b5563;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid rgba(229, 231, 235, 0.3);
}

.tip-item:last-child {
    border-bottom: none;
}

.dark .tip-item {
    color: #d1d5db;
    border-bottom-color: rgba(75, 85, 99, 0.3);
}

.feature-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
}

.feature-item {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.8rem;
    background: rgba(59, 130, 246, 0.05);
    border-radius: 0.8rem;
    transition: all 0.3s ease;
}

.feature-item:hover {
    background: rgba(59, 130, 246, 0.1);
    transform: translateY(-1px);
}

.dark .feature-item {
    background: rgba(96, 165, 250, 0.1);
}

.dark .feature-item:hover {
    background: rgba(96, 165, 250, 0.15);
}

.feature-icon {
    font-size: 1.2rem;
    flex-shrink: 0;
}

.feature-text {
    font-size: 0.85rem;
    font-weight: 600;
    color: #374151;
}

.dark .feature-text {
    color: #e5e7eb;
}

.quick-start {
    margin-top: auto;
    text-align: center;
}

.start-indicator {
    background: linear-gradient(45deg, #10b981, #059669);
    color: white;
    padding: 0.8rem 1.5rem;
    border-radius: 2rem;
    font-weight: 600;
    font-size: 0.9rem;
    display: inline-block;
    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
}

/* ========================
   🔄 进度条系统样式
   ======================== */

.progress-container {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    border: 2px solid #3b82f6;
    border-radius: 1rem;
    padding: 1.5rem;
    margin: 2rem 0;
    display: none;
    box-shadow: 0 8px 25px rgba(59, 130, 246, 0.15);
}

.dark .progress-container {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-color: #60a5fa;
}

.progress-header {
    text-align: center;
    margin-bottom: 1.5rem;
}

.progress-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: #1f2937;
    margin-bottom: 0.5rem;
}

.dark .progress-title {
    color: #f8fafc;
}

.progress-subtitle {
    font-size: 0.9rem;
    color: #6b7280;
}

.dark .progress-subtitle {
    color: #d1d5db;
}

.progress-bar-container {
    background: #e5e7eb;
    border-radius: 1rem;
    height: 8px;
    margin: 1rem 0;
    overflow: hidden;
}

.dark .progress-bar-container {
    background: #374151;
}

.progress-bar {
    background: linear-gradient(90deg, #3b82f6, #10b981);
    height: 100%;
    border-radius: 1rem;
    transition: width 0.5s ease;
    position: relative;
}

.progress-bar::after {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    right: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
    animation: shimmer 2s infinite;
}

@keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

.progress-steps {
    display: flex;
    justify-content: space-between;
    margin: 1.5rem 0;
}

.progress-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
    position: relative;
}

.progress-step-circle {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: #e5e7eb;
    border: 3px solid #e5e7eb;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    transition: all 0.3s ease;
}

.progress-step.active .progress-step-circle {
    background: #3b82f6;
    border-color: #3b82f6;
    color: white;
    animation: pulse 1.5s infinite;
}

.progress-step.completed .progress-step-circle {
    background: #10b981;
    border-color: #10b981;
    color: white;
}

.progress-step-label {
    font-size: 0.8rem;
    margin-top: 0.5rem;
    text-align: center;
    color: #6b7280;
    font-weight: 500;
}

.dark .progress-step-label {
    color: #d1d5db;
}

.progress-step.active .progress-step-label {
    color: #3b82f6;
    font-weight: 700;
}

.progress-step.completed .progress-step-label {
    color: #10b981;
    font-weight: 700;
}

.progress-current-task {
    text-align: center;
    margin: 1rem 0;
}

.progress-task-name {
    font-size: 1.1rem;
    font-weight: 600;
    color: #1f2937;
    margin-bottom: 0.5rem;
}

.dark .progress-task-name {
    color: #f8fafc;
}

.progress-task-details {
    font-size: 0.9rem;
    color: #6b7280;
    margin-bottom: 1rem;
}

.dark .progress-task-details {
    color: #d1d5db;
}

.progress-preview {
    background: rgba(59, 130, 246, 0.05);
    border-radius: 0.8rem;
    padding: 1rem;
    margin-top: 1rem;
}

.dark .progress-preview {
    background: rgba(96, 165, 250, 0.1);
}

.progress-preview-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: #3b82f6;
    margin-bottom: 0.5rem;
}

.dark .progress-preview-title {
    color: #60a5fa;
}

.progress-preview-list {
    list-style: none;
    padding: 0;
    margin: 0;
}

.progress-preview-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.3rem 0;
    font-size: 0.85rem;
    color: #4b5563;
}

.dark .progress-preview-item {
    color: #d1d5db;
}

.progress-preview-item.completed {
    color: #10b981;
}

.progress-preview-item.current {
    color: #3b82f6;
    font-weight: 600;
}

.progress-preview-item.pending {
    color: #9ca3af;
}

/* ========================
   原有样式保持
   ======================== */

/* ========================
   🎯 标题优化
   ======================== */

#input_idea_title h2 {
    color: #1f2937 !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    margin-bottom: 1.5rem !important;
    display: flex !important;
    align-items: center !important;
    gap: 0.5rem !important;
}

.dark #input_idea_title h2 {
    color: #f8fafc !important;
}

/* ========================
   📱 响应式设计
   ======================== */

@media (max-width: 768px) {
    .main-input-row {
        flex-direction: column !important;
    }
    
    .input-column, .tips-column {
        margin: 1rem 0 !important;
        min-height: auto !important;
    }
    
    .feature-grid {
        grid-template-columns: 1fr !important;
    }
    
    .generate-btn-enhanced {
        font-size: 1rem !important;
        padding: 1rem 2rem !important;
    }
}

/* ========================
   原有样式保持
   ======================== */

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

/* 保持原有的所有其他样式... */
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
        <h1>🚀 VibeDoc Agent</h1>
        <p style="font-size: 18px; margin: 10px 0; opacity: 0.95;">
            30秒将创意转化为完整开发方案 + AI编程提示词
        </p>
    </div>
    
    
    <!-- 添加Mermaid.js支持 -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({ 
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose',
            flowchart: {
                useMaxWidth: true,
                htmlLabels: true
            },
            gantt: {
                useMaxWidth: true,
                gridLineStartPadding: 350,
                fontSize: 11,
                fontFamily: '"Open Sans", sans-serif',
                sectionFontSize: 24,
                barHeight: 20,
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
        
        // 强制重新渲染所有Mermaid图表的函数
        function forceRerenderMermaidCharts() {
            // 等待DOM更新后执行
            setTimeout(() => {
                const mermaidElements = document.querySelectorAll('.mermaid');
                mermaidElements.forEach((element, index) => {
                    // 清空并重新初始化
                    element.innerHTML = element.textContent;
                    element.removeAttribute('data-processed');
                    
                    // 为每个图表生成唯一ID
                    if (!element.id) {
                        element.id = `mermaid-chart-${Date.now()}-${index}`;
                    }
                });
                
                // 重新初始化Mermaid
                mermaid.init(undefined, '.mermaid');
                
                // 如果还有未渲染的，再次尝试
                setTimeout(() => {
                    const unprocessedElements = document.querySelectorAll('.mermaid:not([data-processed])');
                    if (unprocessedElements.length > 0) {
                        mermaid.init(undefined, unprocessedElements);
                    }
                }, 1000);
            }, 500);
        }
        
        // 监听内容变化，自动重新渲染图表
        function observeContentChanges() {
            const targetNode = document.getElementById('plan_result');
            if (!targetNode) return;
            
            const observer = new MutationObserver((mutations) => {
                let shouldRerender = false;
                mutations.forEach((mutation) => {
                    if (mutation.type === 'childList' || mutation.type === 'characterData') {
                        const addedNodes = Array.from(mutation.addedNodes);
                        const hasNewContent = addedNodes.some(node => 
                            node.nodeType === Node.ELEMENT_NODE && 
                            (node.textContent.includes('mermaid') || node.querySelector && node.querySelector('.mermaid'))
                        );
                        if (hasNewContent) {
                            shouldRerender = true;
                        }
                    }
                });
                
                if (shouldRerender) {
                    forceRerenderMermaidCharts();
                }
            });
            
            observer.observe(targetNode, {
                childList: true,
                subtree: true,
                characterData: true
            });
        }
        
        // 进度条管理
        let progressContainer = null;
        let progressInterval = null;
        let currentStep = 0;
        
        const progressSteps = [
            {step: 1, name: "🔍 验证输入", details: "检查创意描述和参考链接", items: ["输入验证", "格式检查", "内容分析"]},
            {step: 2, name: "🌐 获取知识", details: "从参考链接获取技术文档", items: ["链接验证", "内容抓取", "知识提取"]},
            {step: 3, name: "🧠 构建提示词", details: "准备AI分析指令", items: ["提示词优化", "上下文构建", "参数配置"]},
            {step: 4, name: "🤖 AI生成中", details: "调用Qwen2.5-72B生成技术方案", items: ["模型调用", "内容生成", "结构化处理"]},
            {step: 5, name: "📋 格式化", details: "美化显示效果，优化图表", items: ["内容美化", "图表渲染", "格式优化"]},
            {step: 6, name: "✅ 完成", details: "创建下载文件，准备展示", items: ["文件创建", "最终检查", "结果展示"]}
        ];
        
        function createProgressHTML(stepIndex) {
            const step = progressSteps[stepIndex];
            const progress = ((stepIndex + 1) / progressSteps.length) * 100;
            const remainingTime = Math.max(0, (progressSteps.length - stepIndex - 1) * 8);
            
            // 生成步骤指示器
            let stepsHTML = '';
            for (let i = 0; i < progressSteps.length; i++) {
                let statusClass, icon;
                if (i < stepIndex) {
                    statusClass = 'completed';
                    icon = '✅';
                } else if (i === stepIndex) {
                    statusClass = 'active';
                    icon = (i + 1).toString();
                } else {
                    statusClass = 'pending';
                    icon = (i + 1).toString();
                }
                
                stepsHTML += `
                <div class="progress-step ${statusClass}">
                    <div class="progress-step-circle">${icon}</div>
                    <div class="progress-step-label">第${i + 1}步</div>
                </div>`;
            }
            
            // 生成预览列表
            let previewHTML = '';
            step.items.forEach((item, idx) => {
                let itemClass, itemIcon;
                const itemProgress = (stepIndex * step.items.length + idx) / (progressSteps.length * step.items.length);
                if (itemProgress < (stepIndex / progressSteps.length)) {
                    itemClass = 'completed';
                    itemIcon = '✅';
                } else if (itemProgress <= ((stepIndex + 1) / progressSteps.length)) {
                    itemClass = 'current';
                    itemIcon = '🔄';
                } else {
                    itemClass = 'pending';
                    itemIcon = '⏳';
                }
                
                previewHTML += `
                <li class="progress-preview-item ${itemClass}">
                    <span>${itemIcon}</span> ${item}
                </li>`;
            });
            
            return `
            <div class="progress-container" style="display: block;">
                <div class="progress-header">
                    <div class="progress-title">🚀 AI正在生成开发方案</div>
                    <div class="progress-subtitle">预计还需 ${remainingTime} 秒</div>
                </div>
                
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: ${progress}%"></div>
                </div>
                
                <div class="progress-steps">
                    ${stepsHTML}
                </div>
                
                <div class="progress-current-task">
                    <div class="progress-task-name">${step.name}</div>
                    <div class="progress-task-details">${step.details}</div>
                </div>
                
                <div class="progress-preview">
                    <div class="progress-preview-title">🎯 生成内容预览</div>
                    <ul class="progress-preview-list">
                        ${previewHTML}
                    </ul>
                </div>
                
                <div class="progress-tips" style="margin-top: 1rem; padding: 1rem; background: rgba(59, 130, 246, 0.05); border-radius: 0.5rem; border-left: 3px solid #3b82f6;">
                    <div style="font-size: 0.9rem; color: #4b5563; margin-bottom: 0.5rem;">💡 <strong>生成过程中，您可以：</strong></div>
                    <div style="font-size: 0.85rem; color: #6b7280; line-height: 1.5;">
                        • 🔍 了解AI正在分析您的创意需求<br>
                        • ⚙️ 准备技术栈和开发环境<br>
                        • 📝 思考项目的具体实施细节<br>
                        • 🎯 规划后续的开发步骤
                    </div>
                </div>
            </div>`;
        }
        
        function startProgress() {
            // 隐藏结果区域，显示进度条
            const planResult = document.getElementById('plan_result');
            if (planResult) {
                planResult.style.display = 'none';
            }
            
            // 创建或获取进度容器
            progressContainer = document.getElementById('progress_container');
            if (!progressContainer) {
                progressContainer = document.createElement('div');
                progressContainer.id = 'progress_container';
                const resultContainer = document.querySelector('.result-container');
                if (resultContainer) {
                    resultContainer.insertBefore(progressContainer, planResult);
                }
            }
            
            currentStep = 0;
            updateProgress();
            
            // 设置定时器更新进度
            const updateProgressStep = () => {
                const nextInterval = (currentStep === 3) ? 35000 : 8000; // AI生成阶段等待35秒，其他步骤8秒
                progressInterval = setTimeout(() => {
                    currentStep++;
                    if (currentStep >= progressSteps.length) {
                        return;
                    }
                    updateProgress();
                    updateProgressStep(); // 递归调用下一步
                }, nextInterval);
            };
            updateProgressStep();
        }
        
        function updateProgress() {
            if (progressContainer && currentStep < progressSteps.length) {
                progressContainer.innerHTML = createProgressHTML(currentStep);
            }
        }
        
        function hideProgress() {
            if (progressInterval) {
                clearTimeout(progressInterval);
                progressInterval = null;
            }
            
            if (progressContainer) {
                progressContainer.style.display = 'none';
            }
            
            const planResult = document.getElementById('plan_result');
            if (planResult) {
                planResult.style.display = 'block';
            }
        }
        
        // 在生成开始时显示进度条
        function showProgressBeforeGeneration() {
            startProgress();
            return true; // 允许继续执行原函数
        }
        
        // 监听主题变化，动态更新Mermaid主题
        function updateMermaidTheme() {
            const isDark = document.documentElement.classList.contains('dark');
            const theme = isDark ? 'dark' : 'default';
            mermaid.initialize({ 
                startOnLoad: true,
                theme: theme,
                securityLevel: 'loose',
                flowchart: {
                    useMaxWidth: true,
                    htmlLabels: true
                },
                gantt: {
                    useMaxWidth: true,
                    gridLineStartPadding: 350,
                    fontSize: 11,
                    fontFamily: '"Open Sans", sans-serif',
                    sectionFontSize: 24,
                    barHeight: 20,
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
            
            // 重新渲染所有图表
            forceRerenderMermaidCharts();
        }
        
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
            observeContentChanges(); // 添加内容变化监听
            
            // 监听主题切换
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                        updateMermaidTheme();
                    }
                });
            });
            observer.observe(document.documentElement, { attributes: true });
            
            // 监听plan_result区域的变化，重新绑定复制按钮和渲染图表
            const contentObserver = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'childList') {
                        bindCopyButtons();
                        // 延迟渲染图表确保内容已完全加载
                        setTimeout(() => {
                            forceRerenderMermaidCharts();
                        }, 1000);
                    }
                });
            });
            
            // 监听plan_result区域的变化
            const planResult = document.getElementById('plan_result');
            if (planResult) {
                contentObserver.observe(planResult, { childList: true, subtree: true });
            }
        });
        
        // 添加手动重新渲染按钮功能
        function manualRerenderCharts() {
            forceRerenderMermaidCharts();
            console.log('手动重新渲染Mermaid图表');
        }
    </script>
    """)
    
    with gr.Row(elem_classes="main-input-row"):
        with gr.Column(scale=3, elem_classes="input-column"):
            gr.Markdown("## 💡 输入您的产品创意", elem_id="input_idea_title")
            
            with gr.Group(elem_classes="input-group"):
                idea_input = gr.Textbox(
                    label="产品创意描述",
                    placeholder="例如：我想做一个帮助程序员管理代码片段的工具，支持多语言语法高亮，可以按标签分类，还能分享给团队成员...",
                    lines=8,
                    max_lines=12,
                    show_label=False,
                    elem_classes="main-input"
                )
                
                reference_url_input = gr.Textbox(
                    label="参考链接 (可选)",
                    placeholder="输入任何网页链接（如博客、新闻、文档）作为参考...",
                    lines=2,
                    show_label=True,
                    elem_classes="url-input"
                )
            
            generate_btn = gr.Button(
                "🚀 AI生成开发计划 + 编程提示词",
                variant="primary",
                size="lg",
                elem_classes="generate-btn-enhanced"
            )
        
        with gr.Column(scale=2, elem_classes="tips-column"):
            gr.HTML("""
            <div class="tips-container">
                <div class="tip-section primary">
                    <h4>💡 输入提示</h4>
                    <div class="tip-items">
                        <div class="tip-item">描述核心功能</div>
                        <div class="tip-item">说明目标用户</div>
                        <div class="tip-item">技术偏好</div>
                    </div>
                </div>
                
                <div class="tip-section secondary">
                    <h4>🎯 输出内容</h4>
                    <div class="feature-grid">
                        <div class="feature-item">
                            <span class="feature-icon">📋</span>
                            <span class="feature-text">开发计划</span>
                        </div>
                        <div class="feature-item">
                            <span class="feature-icon">🤖</span>
                            <span class="feature-text">编程提示词</span>
                        </div>
                        <div class="feature-item">
                            <span class="feature-icon">📊</span>
                            <span class="feature-text">架构图表</span>
                        </div>
                        <div class="feature-item">
                            <span class="feature-icon">📁</span>
                            <span class="feature-text">可下载文档</span>
                        </div>
                    </div>
                </div>
                
                <div class="quick-start">
                    <div class="start-indicator">⚡ 专为开发者设计</div>
                </div>
            </div>
            """)
    
    # 进度条容器
    progress_container = gr.HTML(
        value="",
        visible=False,
        elem_id="progress_container"
    )
    
    # 结果显示区域
    with gr.Column(elem_classes="result-container"):
        plan_output = gr.Markdown(
            value="""
<div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); border-radius: 1rem; border: 2px dashed #cbd5e0;">
    <div style="font-size: 3rem; margin-bottom: 1rem;">🤖</div>
    <h3 style="color: #2b6cb0; margin-bottom: 1rem; font-weight: bold;">输入创意，生成方案</h3>
    <p style="color: #4a5568; font-size: 1.1rem; margin-bottom: 1.5rem;">
        <strong style="color: #e53e3e;">包含：技术方案 • 开发计划 • 部署策略 • AI编程提示词</strong>
    </p>
    <p style="color: #a0aec0; font-size: 0.9rem;">
        点击 <span style="color: #e53e3e; font-weight: bold;">"🚀 AI生成开发计划 + 编程提示词"</span> 开始
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
            rerender_charts_btn = gr.Button(
                "📊 重新渲染图表",
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
            💡 <strong>复制内容到剪贴板，或下载文件保存</strong>
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
        <h3>🤖 编程提示词使用说明</h3>
        <p><strong>支持工具：</strong>Claude Code • GitHub Copilot • ChatGPT • 其他AI编程工具</p>
        <p><em>复制特定提示词，粘贴到AI工具中获得代码实现</em></p>
    </div>
    """)
    
    # Agent应用展示部分
    with gr.Accordion("🤖 技术架构", open=False):
        gr.Markdown("""
### 🎯 **Agent应用特色**

**🔄 工作流程：** 接收输入 → 智能路由 → 多服务协作 → 知识融合 → 结构化输出

**🤖 技术优势：**
- 智能决策路由，多服务协作
- 外部知识与AI深度融合  
- 自适应工作流，容错降级
        """)
        
        gr.Code(
            value="""# Agent应用架构

🤖 VibeDoc Agent (我们的应用):
├── 调用多个MCP服务
├── 智能决策和服务协作  
├── 自适应工作流，多源数据融合
└── 提供完整的业务解决方案

🔧 MCP Server:
├── 被Agent调用的服务
├── 提供特定功能（如DeepWiki、Fetch、Doubao）
├── 标准化接口，专业化能力
└── 为Agent提供可复用组件""",
            language="yaml",
            label="架构说明"
        )
    
    # 绑定事件
    def show_download_info():
        return gr.update(
            value="""
            <div style="padding: 10px; background: #e8f5e8; border-radius: 8px; text-align: center; margin: 10px 0; color: #2d5a2d;" id="download_success_info">
                ✅ <strong style="color: #1a5a1a;">文档已生成！</strong> 
                📋 复制内容 • 📁 下载文档 • 🔄 重新生成
            </div>
            """,
            visible=True
        )
    
    generate_btn.click(
        fn=generate_development_plan_gradio,
        inputs=[idea_input, reference_url_input],
        outputs=[plan_output, prompts_for_copy, download_file, progress_container],
        api_name="generate_plan",
        js="(idea, url) => { showProgressBeforeGeneration(); return [idea, url]; }"
    ).then(
        fn=lambda: gr.update(visible=True),
        outputs=[download_file],
        js="() => { hideProgress(); }"
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
    
    # 图表重新渲染按钮
    rerender_charts_btn.click(
        fn=None,
        inputs=[],
        outputs=[],
        js="""() => {
            manualRerenderCharts();
            alert('🔄 正在重新渲染Mermaid图表...');
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