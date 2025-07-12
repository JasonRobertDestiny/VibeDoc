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
    """生成概念LOGO - 使用模块化配置"""
    doubao_service = config.get_mcp_service("doubao")
    if not doubao_service or not doubao_service.enabled:
        return ""
    
    try:
        logger.info("🎨 使用Doubao MCP生成概念logo...")
        
        # 创建图像提示词
        image_prompt = f"Logo for a new app: {user_idea}, minimalist, vector art, clean background"
        
        # 构建Doubao text_to_image调用的JSON载荷
        image_payload = {
            "action": "text_to_image",
            "params": {
                "prompt": image_prompt,
                "size": "1024x1024"
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
                    logger.info("✅ 概念logo生成成功")
                    return f"\n\n---\n\n## 🎨 概念LOGO\n![Concept Logo]({image_url})"
                else:
                    logger.warning("⚠️ 响应中未找到图像URL")
            else:
                logger.warning("⚠️ 图像生成响应格式无效")
        else:
            logger.error(f"❌ 图像生成失败: HTTP {image_response.status_code}")
            
    except requests.exceptions.Timeout:
        logger.error("⏰ 图像生成超时")
    except requests.exceptions.ConnectionError:
        logger.error("🔌 图像生成连接失败")
    except Exception as e:
        logger.error(f"💥 图像生成错误: {str(e)}")
    
    return ""

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
    
    # 构建系统提示词 - 防止虚假链接生成
    system_prompt = """你是一个资深技术项目经理，精通产品规划和 AI 编程助手（如 GitHub Copilot、ChatGPT Code）提示词撰写。

🔴 重要要求：
1. 当收到外部知识库参考时，你必须在开发计划中明确引用和融合这些信息
2. 必须在开发计划的开头部分提及参考来源（如CSDN博客、GitHub项目等）
3. 必须根据外部参考调整技术选型和实施建议
4. 必须在相关章节中使用"参考XXX建议"等表述

🚫 严禁行为：
- 绝对不要编造虚假的链接或参考资料
- 不要生成不存在的URL（如 xxx.com、example.com等）
- 不要创建虚假的GitHub仓库链接
- 不要引用不存在的CSDN博客文章

✅ 正确做法：
- 如果没有提供外部参考，直接基于创意进行分析
- 只引用用户实际提供的参考链接
- 当外部知识不可用时，明确说明是基于最佳实践生成

🎯 编程提示词格式要求：
- 编程提示词部分必须是纯文本的prompt，不要包含代码示例
- 每个提示词要详细描述需求、约束条件和期望输出
- 格式为：描述 + 具体要求列表 + 输出格式说明
- 提示词要能直接复制粘贴到AI编程工具中使用

请输出结构化的内容，包含：
- 完整的开发计划（Markdown格式，必须融合外部参考）
- 对应的AI编程助手提示词列表（纯prompt格式，不含代码）

格式要求：先输出开发计划，然后输出编程提示词部分。"""

    # 构建用户提示词
    user_prompt = f"""产品创意：{user_idea}"""
    
    # 如果成功获取到外部知识，则注入到提示词中
    if retrieved_knowledge and not retrieved_knowledge.startswith("❌"):
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
    """格式化AI回复，确保包含编程提示词部分并优化视觉呈现"""
    
    # 添加时间戳和格式化标题
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 增强视觉呈现的格式化内容
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
    
    # 如果内容中包含代码示例而不是纯prompt，需要转换格式
    if "```python" in content or "```jsx" in content or "```javascript" in content:
        formatted_content += """

---

<div class="section-divider"></div>

# 🤖 优化后的AI编程助手提示词

<div class="prompts-highlight">

> 💡 **使用说明**：以下提示词可以直接复制到 Claude Code、GitHub Copilot、ChatGPT 等AI编程工具中使用

⚠️ **注意**：原始输出包含了代码示例，以下是转换为标准prompt格式的版本：

## 🔧 核心功能开发提示词

```
请基于上述开发计划，为主要功能模块创建完整的实现代码。

具体要求：
1. 使用开发计划中推荐的技术栈
2. 每个函数都要包含完整的类型注解和文档字符串  
3. 实现完善的错误处理和异常捕获
4. 添加单元测试和集成测试
5. 遵循PEP8代码规范和最佳实践
6. 包含详细的代码注释说明业务逻辑

输出格式：
- 完整的可运行代码
- 必要的依赖安装说明
- 使用示例和测试用例
```

## 🗄️ 数据库设计提示词

```
请根据开发计划中的产品需求，设计完整的数据库架构。

设计要求：
1. 创建详细的实体关系图(ERD)
2. 编写完整的表结构定义SQL(DDL)
3. 设计合理的索引策略提升查询性能
4. 创建数据初始化和迁移脚本
5. 制定数据备份和恢复方案
6. 考虑数据安全和权限控制

输出内容：
- ERD图的文字描述
- 完整的建表SQL语句
- 索引创建语句
- 示例数据插入语句
- 数据库优化建议
```

## 🌐 API接口开发提示词

```
请为项目设计和实现完整的RESTful API接口系统。

开发要求：
1. 设计符合REST规范的API接口
2. 使用OpenAPI/Swagger规范编写API文档
3. 实现标准的HTTP状态码和错误处理
4. 添加请求参数验证和响应格式统一
5. 实现JWT认证和权限控制
6. 编写完整的接口测试用例

交付物：
- API接口的完整实现代码
- OpenAPI文档(YAML格式)
- 接口测试用例
- 部署和使用说明
- 性能优化建议
```

## 🎨 前端界面开发提示词

```
请基于开发计划创建现代化的前端用户界面。

设计要求：
1. 实现响应式设计，适配桌面和移动设备
2. 使用现代化UI组件库(如Material-UI、Ant Design)
3. 实现流畅的用户交互和动画效果
4. 支持国际化(i18n)和主题切换
5. 优化页面加载性能和用户体验
6. 确保可访问性(a11y)标准

输出内容：
- 完整的组件代码
- 样式文件(CSS/SCSS)
- 状态管理实现
- 路由配置
- 性能优化方案
- 测试用例
```

## 🧪 测试开发提示词

```
请为项目创建完整的测试体系。

测试要求：
1. 编写单元测试覆盖核心业务逻辑
2. 实现集成测试验证模块间协作
3. 创建端到端(E2E)测试模拟用户操作
4. 设置自动化测试流程和CI/CD集成
5. 实现性能测试和压力测试
6. 添加代码覆盖率检查

交付内容：
- 完整的测试代码
- 测试配置文件
- 测试数据和Mock设置
- 自动化测试脚本
- 测试报告模板
- 测试最佳实践文档
```

</div>

---

**💡 使用提示：** 复制任一提示词到AI编程工具中，它们会根据具体需求生成对应的代码实现！
"""
    
    return formatted_content

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
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 30px;
    border-radius: 15px;
    text-align: center;
    margin-bottom: 30px;
}

.content-card {
    background: white;
    padding: 25px;
    border-radius: 15px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    margin: 20px 0;
}

.result-container {
    background: #f8f9fa;
    border-radius: 10px;
    padding: 20px;
    margin: 20px 0;
    border-left: 4px solid #007bff;
}

.generate-btn {
    background: linear-gradient(45deg, #007bff, #0056b3) !important;
    border: none !important;
    color: white !important;
    padding: 15px 30px !important;
    border-radius: 25px !important;
    font-weight: bold !important;
    font-size: 16px !important;
    transition: all 0.3s ease !important;
}

.generate-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 20px rgba(0,123,255,0.3) !important;
}

.tips-box {
    background: #e3f2fd;
    padding: 20px;
    border-radius: 10px;
    margin: 20px 0;
}

.tips-box h4 {
    color: #1976d2;
    margin-bottom: 15px;
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

/* Improve placeholder text contrast in dark mode */
.dark #plan_output_area textarea::placeholder {
    color: #9CA3AF !important;
}

/* Improve AI helper text contrast in dark mode */
.dark #ai_helper_instructions {
    color: #CBD5E0 !important;
}

.dark #ai_helper_instructions p {
    color: #E2E8F0 !important;
}

.dark #ai_helper_instructions li {
    color: #E2E8F0 !important;
}

.dark #ai_helper_instructions strong {
    color: #F7FAFC !important;
}

/* Improve plan output placeholder text contrast in dark mode */
.dark #plan_output_area {
    color: #E2E8F0 !important;
}

.dark #plan_output_area p {
    color: #E2E8F0 !important;
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
    title="VibeDoc - MCP开发计划生成器",
    theme=gr.themes.Soft(primary_hue="blue"),
    css=custom_css
) as demo:
    
    gr.HTML("""
    <div class="header-gradient">
        <h1>🚀 VibeDoc - AI Agent开发计划生成器</h1>
        <p style="font-size: 18px; margin: 15px 0; opacity: 0.95;">
            基于AI的Agent应用，集成多种MCP服务提供智能开发计划生成
        </p>
        <p style="opacity: 0.85;">
            一键将创意转化为完整的开发方案 + AI编程助手提示词，展示Agent应用与MCP服务协作能力
        </p>
    </div>
    """)
    
    with gr.Row():
        with gr.Column(scale=2, elem_classes="content-card"):
            gr.Markdown("## 💡 输入您的产品创意")
            
            idea_input = gr.Textbox(
                label="产品创意描述",
                placeholder="例如：我想做一个帮助程序员管理代码片段的工具，支持多语言语法高亮，可以按标签分类，还能分享给团队成员...",
                lines=5,
                max_lines=10,
                show_label=False
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
                <h4>💡 创意提示</h4>
                <ul>
                    <li>描述核心功能和特性</li>
                    <li>说明目标用户群体</li>
                    <li>提及技术偏好或限制</li>
                    <li>描述主要使用场景</li>
                    <li>可以包含商业模式想法</li>
                </ul>
                <h4>🎯 AI增强功能</h4>
                <ul>
                    <li>📋 完整开发计划生成</li>
                    <li>🤖 AI编程助手提示词</li>
                    <li>📝 可直接用于编程工具</li>
                    <li>🔗 智能参考链接解析</li>
                    <li>🎨 专业文档格式化</li>
                </ul>
                <h4>📖 使用建议</h4>
                <ul>
                    <li>✍️ 详细描述产品创意(10字以上)</li>
                    <li>🔗 提供相关参考链接(可选)</li>
                    <li>🎯 明确目标用户和使用场景</li>
                    <li>⚡ 30秒即可获得完整方案</li>
                </ul>
            </div>
            """)
    
    # 结果显示区域
    with gr.Column(elem_classes="result-container"):
        plan_output = gr.Markdown(
            value="💭 **AI生成的完整开发计划和编程提示词将在这里显示...**\n\n点击上方按钮开始生成您的专属开发计划和对应的AI编程助手提示词！",
            elem_id="plan_output_area",
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
        <div style="padding: 10px; background: #e3f2fd; border-radius: 8px; text-align: center;">
            💡 <strong>使用提示</strong>: 点击上方按钮复制内容到剪贴板，或使用下方下载功能保存为文件。
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
    
    # Agent应用展示部分
    with gr.Accordion("🤖 Agent应用架构说明", open=False):
        gr.Markdown("""
### 🎯 **Agent应用特色**

VibeDoc 是一个展示 **Agent应用** 能力的典型案例：

**🔄 Agent工作流程：**
1. **接收用户输入** - 处理产品创意和参考链接
2. **智能路由决策** - 根据URL类型选择合适的MCP服务
3. **多服务协作** - 调用DeepWiki、Fetch、Doubao等MCP服务
4. **知识融合处理** - 将外部知识与AI推理结合
5. **结构化输出** - 生成完整的开发计划和编程助手提示词

**🤖 与传统应用的区别：**
- ❌ **传统应用**: 固定的处理逻辑，单一的数据源
- ✅ **Agent应用**: 智能决策路由，多服务协作，自适应工作流

**🌟 技术亮点：**
- 🧠 智能服务路由算法
- 🔗 多MCP服务无缝集成  
- 🛡️ 完善的容错降级机制
- 📊 知识增强的AI生成
        """)
        
        gr.Code(
            value="""# Agent应用 vs MCP Server 的区别

🤖 Agent应用 (我们的VibeDoc):
├── 使用者: 调用多个MCP服务
├── 职责: 智能决策和服务协作
├── 特点: 自适应工作流，多源数据融合
└── 价值: 提供完整的业务解决方案

🔧 MCP Server:
├── 提供者: 被Agent应用调用
├── 职责: 提供特定功能服务
├── 特点: 标准化接口，专业化能力
└── 价值: 为Agent提供可复用的组件

💡 VibeDoc展示了Agent如何智能地协调多个MCP服务，
   实现比单个服务更强大的综合能力！""",
            language="yaml",
            label="Agent应用架构说明"
        )
    
    # 绑定事件
    def show_download_info():
        return gr.update(
            value="""
            <div style="padding: 10px; background: #e8f5e8; border-radius: 8px; text-align: center; margin: 10px 0;">
                ✅ <strong>文档已生成！</strong> 您现在可以：
                <br>• 📋 复制开发计划或编程提示词
                <br>• 📁 点击下方下载按钮保存文档
                <br>• 🔄 调整创意重新生成
            </div>
            """,
            visible=True
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