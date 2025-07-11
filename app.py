import gradio as gr
import requests
import os
import logging
import json
import tempfile
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API配置 - 仅使用环境变量
API_KEY = os.environ.get("SILICONFLOW_API_KEY")
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
DEEPWIKI_SSE_URL = os.environ.get("DEEPWIKI_SSE_URL")
FETCH_SSE_URL = os.environ.get("FETCH_SSE_URL")
DOUBAO_SSE_URL = os.environ.get("DOUBAO_SSE_URL")
DOUBAO_API_KEY = os.environ.get("DOUBAO_API_KEY")

# 设置Doubao API Key（应用启动时）
if DOUBAO_SSE_URL and DOUBAO_API_KEY:
    logger.info("Setting Doubao API Key on startup...")
    try:
        requests.post(
            DOUBAO_SSE_URL,
            json={"action": "set_api_key", "params": {"api_key": DOUBAO_API_KEY}},
            timeout=10
        )
        logger.info("Doubao API Key set successfully")
    except Exception as e:
        logger.error(f"Failed to set Doubao API Key: {e}")

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
        logger.info(f"Calling {service_name} MCP service...")
        
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            if "data" in data and data["data"]:
                content = data["data"]
                logger.info(f"{service_name} MCP service returned {len(content)} characters")
                return True, content
            else:
                logger.warning(f"{service_name} MCP service returned empty data")
                return False, f"❌ {service_name} MCP返回空数据"
        else:
            logger.error(f"{service_name} MCP service failed with status {response.status_code}")
            return False, f"❌ {service_name} MCP调用失败: HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        logger.error(f"{service_name} MCP service timeout")
        return False, f"❌ {service_name} MCP调用超时"
    except requests.exceptions.ConnectionError:
        logger.error(f"{service_name} MCP service connection failed")
        return False, f"❌ {service_name} MCP连接失败"
    except Exception as e:
        logger.error(f"{service_name} MCP service error: {str(e)}")
        return False, f"❌ {service_name} MCP调用错误: {str(e)}"

def fetch_external_knowledge(reference_url: str) -> str:
    """获取外部知识库内容"""
    if not reference_url or not reference_url.strip():
        return ""
    
    url = reference_url.strip()
    
    # 验证URL格式
    if not validate_url(url):
        logger.warning(f"Invalid URL format: {url}")
        return "❌ 无效的URL格式"
    
    # 智能路由：根据URL类型选择不同的MCP服务
    if "deepwiki.org" in url:
        if not DEEPWIKI_SSE_URL:
            logger.error("DEEPWIKI_SSE_URL not configured")
            return "❌ DeepWiki服务未配置"
        
        payload = {
            "action": "deepwiki_fetch",
            "params": {
                "url": url,
                "mode": "aggregate"
            }
        }
        
        success, knowledge = call_mcp_service(DEEPWIKI_SSE_URL, payload, "DeepWiki")
        return knowledge
    
    else:
        if not FETCH_SSE_URL:
            logger.error("FETCH_SSE_URL not configured")
            return "❌ Fetch服务未配置"
        
        payload = {
            "action": "fetch",
            "params": {
                "url": url
            }
        }
        
        success, knowledge = call_mcp_service(FETCH_SSE_URL, payload, "Fetch")
        return knowledge

def generate_concept_logo(user_idea: str) -> str:
    """生成概念LOGO"""
    if not DOUBAO_SSE_URL or not DOUBAO_API_KEY:
        return ""
    
    try:
        logger.info("Generating concept logo with Doubao...")
        
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
            DOUBAO_SSE_URL,
            json=image_payload,
            timeout=30
        )
        
        if image_response.status_code == 200:
            image_data = image_response.json()
            # 解析图像URL（根据实际响应格式调整）
            if "result" in image_data and image_data["result"] and len(image_data["result"]) > 0:
                image_url = image_data["result"][0].get("url", "")
                if image_url:
                    logger.info("Concept logo generated successfully")
                    return f"\n\n---\n\n## 🎨 概念LOGO\n![Concept Logo]({image_url})"
                else:
                    logger.warning("No image URL found in response")
            else:
                logger.warning("Invalid image generation response format")
        else:
            logger.error(f"Image generation failed: HTTP {image_response.status_code}")
            
    except requests.exceptions.Timeout:
        logger.error("Image generation timeout")
    except requests.exceptions.ConnectionError:
        logger.error("Image generation connection failed")
    except Exception as e:
        logger.error(f"Image generation error: {str(e)}")
    
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
        return "❌ 错误：未配置API密钥", "", ""
    
    # 获取外部知识库内容
    retrieved_knowledge = fetch_external_knowledge(reference_url)
    
    # 构建系统提示词
    system_prompt = """你是一个资深技术项目经理，精通产品规划和 AI 编程助手（如 GitHub Copilot、ChatGPT Code）提示词撰写。当收到一个产品创意时，你要：

1. 生成一个详细的开发计划（Markdown 格式，包含功能、技术栈、时间节点等）
2. 针对计划中的每个功能点，生成一条可直接输入给 AI 编程助手的提示词（Prompt），说明要实现的功能、输入输出、关键依赖等

请输出结构化的内容，包含：
- 完整的开发计划（Markdown格式）
- 对应的AI编程助手提示词列表

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
    
    # 在内容开头添加生成信息
    formatted_content = f"""
---

# 🚀 AI生成的开发计划

**⏰ 生成时间：** {timestamp}  
**🤖 AI模型：** Qwen2.5-72B-Instruct  
**💡 基于用户创意智能分析生成**

---

{content}
"""
    
    # 如果内容中没有明确的编程提示词部分，添加一个格式化的分隔符
    if "编程提示词" not in content and "编程助手" not in content and "Prompt" not in content:
        formatted_content += """

---

<div class="section-divider"></div>

# 🤖 AI编程助手提示词

<div class="prompts-highlight">

> 💡 **使用说明**：以下提示词可以直接复制到 Claude Code、GitHub Copilot、ChatGPT 等AI编程工具中使用

## 🔧 核心功能开发提示词

```bash
基于上述开发计划，请为每个主要功能模块生成具体的实现代码。

📋 要求：
• 使用推荐的技术栈
• 包含完整的错误处理
• 添加必要的注释和文档
• 遵循最佳实践和安全规范
• 确保代码可读性和可维护性
```

## 🗄️ 数据库设计提示词

```sql
根据产品需求设计完整的数据库架构：

📊 包含内容：
• 实体关系图(ERD)设计
• 完整的表结构定义(DDL)
• 索引优化策略
• 数据迁移和初始化脚本
• 数据备份和恢复方案
```

## 🌐 API接口开发提示词

```javascript
设计和实现完整的RESTful API接口系统：

🔗 开发要求：
• 完整的API文档(OpenAPI/Swagger)
• 详细的请求/响应示例
• 标准化的错误码定义
• 完整的接口测试用例
• API版本控制策略
```

## 🎨 前端界面开发提示词

```css
基于开发计划创建现代化的用户界面：

🎯 设计目标：
• 响应式设计，支持多设备
• 现代化UI组件和交互
• 无障碍访问支持
• 性能优化和用户体验
• 国际化和主题切换
```

</div>

---

**💡 提示：** 将上述任一提示词复制到AI编程工具中，即可获得针对性的代码实现方案！
"""
    
    return formatted_content

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
}

#plan_result h3 {
    font-size: 1.5rem;
    font-weight: 600;
    color: #4a5568;
    margin-top: 1.5rem;
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
}

#plan_result h4 {
    font-size: 1.25rem;
    font-weight: 600;
    color: #5a67d8;
    margin-top: 1.25rem;
    margin-bottom: 0.5rem;
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
"""

# 保持美化的Gradio界面
with gr.Blocks(
    title="VibeDoc - MCP开发计划生成器",
    theme=gr.themes.Soft(primary_hue="blue"),
    css=custom_css
) as demo:
    
    gr.HTML("""
    <div class="header-gradient">
        <h1>🚀 VibeDoc - AI开发计划生成器</h1>
        <p style="font-size: 18px; margin: 15px 0; opacity: 0.95;">
            基于AI的产品开发计划生成工具，支持MCP协议
        </p>
        <p style="opacity: 0.85;">
            一键将创意转化为完整的开发方案 + AI编程助手提示词，可被Claude等AI助手调用
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
                <h4>🎯 新增功能</h4>
                <ul>
                    <li>📋 完整开发计划</li>
                    <li>🤖 AI编程助手提示词</li>
                    <li>📝 可直接用于编程工具</li>
                    <li>🔗 智能参考链接解析</li>
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
        download_file = gr.File(label="下载开发计划文档", visible=False)
        
        # 新的交互按钮
        with gr.Row():
            copy_full_button = gr.Button("📋 复制完整内容", variant="secondary")
            copy_prompts_button = gr.Button("🤖 复制编程提示词", variant="secondary")
        
    # 示例区域
    gr.Markdown("## 🎯 快速开始示例", elem_id="quick_start_container")
    gr.Examples(
        examples=[
            ["我想开发一个基于AI的代码审查工具，能够自动检测代码质量问题并给出优化建议，支持多种编程语言"],
            ["创建一个在线协作的思维导图工具，支持实时编辑、多人同步、版本控制和导出功能"],
            ["开发一个专门为小团队设计的项目管理平台，集成时间追踪、报告生成和团队协作功能"],
            ["制作一个学习编程的互动平台，通过游戏化方式教授编程概念，包含练习和评估系统"]
        ],
        inputs=[idea_input],
        label="点击示例快速开始",
        examples_per_page=4
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
    
    # MCP测试部分
    with gr.Accordion("🔧 如何通过API或MCP使用本工具", open=False):
        gr.Code(
            value="""# 将 YOUR_APP_URL 替换为您的创空间URL, 比如 https://jasonrobert-vibedocs.modelscope.cn
# 将 YOUR_IDEA 替换为您的产品创意
curl -X POST YOUR_APP_URL/api/generate_plan -H "Content-Type: application/json" -d '{"data": ["YOUR_IDEA"]}'""",
            language="shell",
            label="MCP API调用示例"
        )
        gr.Markdown("""
**使用说明：**
1. 将 `YOUR_APP_URL` 替换为您的创空间实际URL
2. 将 `YOUR_IDEA` 替换为您的产品创意描述  
3. 在终端或命令行中执行此命令即可获得JSON格式的开发计划
4. 此API也可以被其他MCP客户端调用，实现自动化开发计划生成
        """)
    
    # 绑定事件
    generate_btn.click(
        fn=generate_development_plan,
        inputs=[idea_input, reference_url_input],
        outputs=[plan_output, prompts_for_copy, download_file],
        api_name="generate_plan"
    ).then(
        fn=lambda: gr.update(visible=True),
        outputs=[download_file]
    )
    
    # 复制按钮事件
    copy_full_button.click(
        fn=None,
        _js="(text) => { navigator.clipboard.writeText(text); alert('✅ 完整内容已复制到剪贴板！'); }",
        inputs=[plan_output]
    )
    
    copy_prompts_button.click(
        fn=None,
        _js="(text) => { navigator.clipboard.writeText(text); alert('🤖 AI编程提示词已复制到剪贴板！\\n\\n可以直接粘贴到Claude Code、GitHub Copilot等AI编程工具中使用。'); }",
        inputs=[prompts_for_copy]
    )

# 启动应用
if __name__ == "__main__":
    demo.launch(mcp_server=True)