import gradio as gr
import requests
import os
import logging
import json
from datetime import datetime

# 配置简洁日志
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# API配置
API_KEY = os.environ.get("SILICONFLOW_API_KEY", "sk-eeqxcykxvmomeunmpbbgdsqgvrxqksyapauxzexphsiflgsy")
API_URL = "https://api.siliconflow.cn/v1/chat/completions"

def generate_development_plan(user_idea: str) -> str:
    """
    基于用户创意生成完整的产品开发计划和对应的AI编程助手提示词。
    
    Args:
        user_idea (str): 用户的产品创意描述，可以是任何类型的应用或服务想法
        
    Returns:
        str: 包含开发计划和AI编程提示词的完整方案，采用结构化的Markdown格式
    """
    if not user_idea or not user_idea.strip():
        return "❌ 请输入您的产品创意！"
        
    if not API_KEY:
        return "❌ 错误：未配置API密钥"

    # 使用二段式提示词，生成开发计划和编程提示词
    system_prompt = """你是一个资深技术项目经理，精通产品规划和 AI 编程助手（如 GitHub Copilot、ChatGPT Code）提示词撰写。当收到一个产品创意时，你要：

1. 生成一个详细的开发计划（Markdown 格式，包含功能、技术栈、时间节点等）
2. 针对计划中的每个功能点，生成一条可直接输入给 AI 编程助手的提示词（Prompt），说明要实现的功能、输入输出、关键依赖等

请输出结构化的内容，包含：
- 完整的开发计划（Markdown格式）
- 对应的AI编程助手提示词列表

格式要求：先输出开发计划，然后输出编程提示词部分。"""

    user_prompt = f"""产品创意：{user_idea}

请生成：
1. 详细的开发计划（包含产品概述、技术方案、开发计划、部署方案、推广策略等）
2. 每个功能模块对应的AI编程助手提示词

确保提示词具体、可操作，能直接用于AI编程工具。"""

    try:
        response = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "Qwen/Qwen2.5-72B-Instruct",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 4000,  # 增加token数以容纳更多内容
                "temperature": 0.7
            },
            timeout=120
        )
        
        if response.status_code == 200:
            content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                # 后处理：确保内容结构化
                return format_response(content)
            else:
                return "❌ API返回空内容"
        else:
            return f"❌ API请求失败: HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        return "❌ API请求超时，请稍后重试。网络可能较慢，建议检查网络连接。"
    except requests.exceptions.ConnectionError:
        return "❌ 网络连接失败，请检查网络设置"
    except Exception as e:
        return f"❌ 处理错误: {str(e)}"

def format_response(content: str) -> str:
    """格式化AI回复，确保包含编程提示词部分"""
    
    # 如果内容中没有明确的编程提示词部分，添加一个分隔符
    if "编程提示词" not in content and "编程助手" not in content and "Prompt" not in content:
        content += """

---

## 🤖 AI编程助手提示词

> 💡 **使用说明**：以下提示词可以直接复制到 Claude Code、GitHub Copilot、ChatGPT 等AI编程工具中使用

### 核心功能开发提示词
```
基于上述开发计划，请为每个主要功能模块生成具体的实现代码。
要求：
1. 使用推荐的技术栈
2. 包含完整的错误处理
3. 添加必要的注释
4. 遵循最佳实践和安全规范
```

### 数据库设计提示词  
```
根据产品需求设计数据库结构，包括：
1. 实体关系图(ERD)
2. 表结构定义(DDL)
3. 索引优化建议
4. 数据迁移脚本
```

### API接口开发提示词
```
设计和实现RESTful API接口，要求：
1. 完整的接口文档
2. 请求/响应示例
3. 错误码定义
4. 接口测试用例
```"""
    
    return content

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
                </ul>
            </div>
            """)
    
    # 结果显示区域
    with gr.Column(elem_classes="result-container"):
        plan_output = gr.Markdown(
            value="💭 **AI生成的完整开发计划和编程提示词将在这里显示...**\n\n点击上方按钮开始生成您的专属开发计划和对应的AI编程助手提示词！",
            elem_id="plan_result"
        )
        
        # 操作按钮 - 使用纯JavaScript避免lambda函数暴露
        with gr.Row():
            gr.HTML("""
            <button onclick="copyFullContent()" style="
                background: #6c757d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                margin: 5px;
                font-size: 14px;
            ">📋 复制完整内容</button>
            
            <button onclick="copyPrompts()" style="
                background: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                margin: 5px;
                font-size: 14px;
            ">🤖 复制编程提示词</button>
            
            <script>
            function copyFullContent() {
                const planResult = document.getElementById('plan_result');
                if (planResult) {
                    const content = planResult.innerText || planResult.textContent;
                    if (content && !content.includes('AI生成的完整开发计划和编程提示词将在这里显示')) {
                        navigator.clipboard.writeText(content).then(function() {
                            alert('✅ 完整内容已复制到剪贴板！');
                        }).catch(function(err) {
                            alert('❌ 复制失败，请手动复制');
                        });
                    } else {
                        alert('⚠️ 请先生成开发计划');
                    }
                }
            }
            
            function copyPrompts() {
                const planResult = document.getElementById('plan_result');
                if (planResult) {
                    const content = planResult.innerText || planResult.textContent;
                    if (content && !content.includes('AI生成的完整开发计划和编程提示词将在这里显示')) {
                        const lines = content.split('\\n');
                        let promptsSection = [];
                        let inPromptsSection = false;
                        
                        for (let line of lines) {
                            if (line.includes('编程提示词') || line.includes('编程助手') || line.includes('Prompt')) {
                                inPromptsSection = true;
                            }
                            if (inPromptsSection) {
                                promptsSection.push(line);
                            }
                        }
                        
                        const promptsText = promptsSection.join('\\n');
                        if (promptsText.trim()) {
                            navigator.clipboard.writeText(promptsText).then(function() {
                                alert('🤖 AI编程提示词已复制到剪贴板！\\n\\n可以直接粘贴到Claude Code、GitHub Copilot等AI编程工具中使用。');
                            }).catch(function(err) {
                                alert('❌ 复制失败，请手动复制编程提示词部分');
                            });
                        } else {
                            alert('⚠️ 未找到编程提示词部分，请检查生成的内容');
                        }
                    } else {
                        alert('⚠️ 请先生成开发计划');
                    }
                }
            }
            </script>
            """)
    
    # 示例区域
    gr.Markdown("## 🎯 快速开始示例")
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
    <div class="prompts-section">
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
    
    # 绑定事件 - 只有主函数使用api_name
    generate_btn.click(
        fn=generate_development_plan,
        inputs=[idea_input],
        outputs=[plan_output],
        api_name="generate_plan"  # 确保MCP只识别主函数
    )

# 学习您工作项目的简单直接启动方式
demo.launch(mcp_server=True)