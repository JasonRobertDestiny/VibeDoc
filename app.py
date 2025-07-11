import gradio as gr
import requests
import os
import json
import logging
import sys
import time

# 配置简洁日志
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API配置
API_KEY = os.environ.get("SILICONFLOW_API_KEY", "sk-eeqxcykxvmomeunmpbbgdsqgvrxqksyapauxzexphsiflgsy")
API_URL = "https://api.siliconflow.cn/v1/chat/completions"

def generate_development_plan(user_idea: str) -> str:
    """
    基于用户创意生成完整的产品开发计划，包括技术方案、部署策略和推广方案。
    
    Args:
        user_idea (str): 用户的产品创意描述，可以是任何类型的应用或服务想法
        
    Returns:
        str: 结构化的Markdown格式开发计划，包含产品分析、技术栈推荐、开发步骤、部署方案和推广策略
    """
    if not user_idea or not user_idea.strip():
        return "❌ 请输入您的产品创意！"
        
    if not API_KEY:
        return "❌ 错误：未配置API密钥，请设置SILICONFLOW_API_KEY环境变量"

    # 优化的提示词，专注于MCP Server开发
    master_prompt = f"""你是一位资深的产品经理和全栈开发专家。基于用户想法生成专业的开发计划。

用户想法：{user_idea}

请生成一份结构化的Markdown开发计划，包含：

## 🎯 产品概述
- 核心功能和价值主张
- 目标用户分析
- 市场竞品分析

## 🛠️ 技术方案
- 推荐技术栈（前端/后端/数据库）
- 系统架构设计
- 关键技术难点

## 📋 开发计划
- 功能模块拆分
- 开发优先级排序
- 时间规划建议

## 🚀 部署上线
- 推荐部署平台
- 域名和SSL配置
- 性能优化建议

## 📈 推广运营
- 目标渠道策略
- 内容营销建议
- 用户增长方案

## 🔧 MCP Server集成
- 如何将此项目转化为MCP工具
- 可提供的AI助手功能
- 与Claude等AI的集成方案

保持专业且实用，每个部分提供具体可执行的建议。"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "messages": [{"role": "user", "content": master_prompt}],
        "max_tokens": 3000,
        "temperature": 0.7,
        "stream": False
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        
        if response.status_code != 200:
            return f"❌ API请求失败: HTTP {response.status_code}"
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        return content if content else "❌ API返回空内容，请稍后重试"
        
    except requests.exceptions.Timeout:
        return "❌ 请求超时，请稍后重试"
    except Exception as e:
        return f"❌ 处理错误: {str(e)}"

def analyze_project_feasibility(project_description: str, budget: str, timeline: str) -> str:
    """
    分析项目的可行性，提供技术难度评估和资源需求分析。
    
    Args:
        project_description (str): 项目详细描述
        budget (str): 预算范围（如：1万以下、1-5万、5万以上）
        timeline (str): 期望完成时间（如：1个月、3个月、6个月）
        
    Returns:
        str: 项目可行性分析报告，包含技术难度、资源评估和实施建议
    """
    if not all([project_description.strip(), budget.strip(), timeline.strip()]):
        return "❌ 请填写完整的项目信息"
    
    prompt = f"""作为技术顾问，分析以下项目的可行性：

项目描述：{project_description}
预算范围：{budget}
完成时间：{timeline}

请提供：
## 📊 可行性评估
- 技术难度等级（1-5星）
- 开发复杂度分析

## 💰 资源需求
- 人力成本评估
- 技术成本分析
- 第三方服务费用

## ⚠️ 风险评估
- 主要技术风险
- 时间风险分析
- 预算超支可能性

## 💡 优化建议
- MVP功能建议
- 成本控制方案
- 时间管理策略

## 🎯 实施路径
- 分阶段开发计划
- 关键里程碑设定"""

    # 简化API调用逻辑
    try:
        response = requests.post(API_URL, 
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "Qwen/Qwen2.5-72B-Instruct",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2500,
                "temperature": 0.7
            },
            timeout=45
        )
        
        if response.status_code == 200:
            return response.json().get("choices", [{}])[0].get("message", {}).get("content", "❌ API返回空内容")
        else:
            return f"❌ API请求失败: {response.status_code}"
            
    except Exception as e:
        return f"❌ 分析失败: {str(e)}"

# 创建现代化的Gradio界面
def create_modern_ui():
    # 自定义CSS样式
    custom_css = """
    .main-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }
    .header-section {
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 30px;
        border-radius: 15px;
        margin-bottom: 30px;
    }
    .feature-card {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #007bff;
        margin: 10px 0;
    }
    .input-section {
        background: white;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 20px 0;
    }
    .output-section {
        background: #f8f9fa;
        border-radius: 15px;
        padding: 20px;
        margin: 20px 0;
    }
    .gradio-button {
        background: linear-gradient(45deg, #007bff, #0056b3) !important;
        border: none !important;
        color: white !important;
        padding: 12px 30px !important;
        border-radius: 25px !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
    }
    .gradio-button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 5px 15px rgba(0,123,255,0.3) !important;
    }
    """
    
    with gr.Blocks(
        title="VibeDoc - MCP开发计划生成器",
        theme=gr.themes.Soft(primary_hue="blue", secondary_hue="cyan"),
        css=custom_css
    ) as demo:
        
        # 头部介绍
        gr.HTML("""
        <div class="header-section">
            <h1>🚀 VibeDoc - AI驱动的MCP开发计划生成器</h1>
            <p style="font-size: 18px; margin: 20px 0;">
                参赛魔搭AI Hackathon 2025 | MCP Server开发赛道
            </p>
            <p style="opacity: 0.9;">
                一键将创意转化为完整的开发方案，支持MCP协议，可被Claude等AI助手调用
            </p>
        </div>
        """)
        
        # 功能特色展示
        gr.HTML("""
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 30px 0;">
            <div class="feature-card">
                <h3>🤖 AI智能分析</h3>
                <p>基于Qwen2.5-72B大模型，深度分析用户需求</p>
            </div>
            <div class="feature-card">
                <h3>📋 完整方案</h3>
                <p>涵盖技术选型、开发计划、部署运营全流程</p>
            </div>
            <div class="feature-card">
                <h3>🔧 MCP集成</h3>
                <p>原生支持MCP协议，可被AI助手直接调用</p>
            </div>
            <div class="feature-card">
                <h3>🚀 快速部署</h3>
                <p>一键部署到ModelScope，无需复杂配置</p>
            </div>
        </div>
        """)
        
        # 主要功能区域
        with gr.Tabs() as main_tabs:
            
            # Tab 1: 开发计划生成
            with gr.Tab("💡 创意转开发计划", elem_classes="input-section"):
                gr.Markdown("### 输入您的产品创意，AI将生成完整的开发计划")
                
                with gr.Row():
                    with gr.Column(scale=3):
                        idea_input = gr.Textbox(
                            label="🎯 产品创意描述",
                            placeholder="例如：我想做一个帮助程序员管理代码片段的工具，支持多语言语法高亮，可以按标签分类，还能分享给团队成员...",
                            lines=4,
                            max_lines=8,
                            show_label=True
                        )
                        
                        generate_btn = gr.Button(
                            "🤖 AI生成开发计划",
                            variant="primary",
                            size="lg",
                            elem_classes="gradio-button"
                        )
                    
                    with gr.Column(scale=1):
                        gr.HTML("""
                        <div style="background: #e3f2fd; padding: 20px; border-radius: 10px;">
                            <h4>💡 创意提示</h4>
                            <ul style="margin: 10px 0;">
                                <li>描述核心功能</li>
                                <li>说明目标用户</li>
                                <li>提及技术偏好</li>
                                <li>描述使用场景</li>
                            </ul>
                        </div>
                        """)
                
                plan_output = gr.Markdown(
                    label="📋 生成的开发计划",
                    value="💭 AI生成的完整开发计划将在这里显示...",
                    elem_classes="output-section"
                )
                
                # 示例区域
                gr.Examples(
                    examples=[
                        ["我想开发一个基于AI的代码审查工具，能够自动检测代码质量问题并给出优化建议"],
                        ["创建一个在线协作的思维导图工具，支持实时编辑和多人同步"],
                        ["开发一个专门为小团队设计的项目管理平台，集成了时间追踪和报告功能"],
                        ["制作一个学习编程的互动平台，通过游戏化的方式教授编程概念"]
                    ],
                    inputs=[idea_input],
                    label="🎯 点击示例快速开始"
                )
            
            # Tab 2: 可行性分析
            with gr.Tab("📊 项目可行性分析", elem_classes="input-section"):
                gr.Markdown("### 评估项目的技术难度、资源需求和实施风险")
                
                with gr.Row():
                    with gr.Column():
                        project_desc = gr.Textbox(
                            label="📝 项目详细描述",
                            placeholder="详细描述您的项目需求、功能特性和技术要求...",
                            lines=4
                        )
                        
                        with gr.Row():
                            budget_input = gr.Dropdown(
                                choices=["1万以下", "1-5万", "5-10万", "10万以上", "预算充足"],
                                label="💰 预算范围",
                                value="1-5万"
                            )
                            
                            timeline_input = gr.Dropdown(
                                choices=["1个月内", "3个月内", "6个月内", "1年内", "时间充裕"],
                                label="⏰ 完成时间",
                                value="3个月内"
                            )
                        
                        analyze_btn = gr.Button(
                            "📊 开始可行性分析",
                            variant="secondary",
                            size="lg"
                        )
                
                analysis_output = gr.Markdown(
                    label="📊 可行性分析报告",
                    value="📈 详细的项目可行性分析报告将在这里显示...",
                    elem_classes="output-section"
                )
        
        # 底部信息
        gr.HTML("""
        <div style="text-align: center; margin-top: 40px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
            <h3>🏆 关于VibeDoc MCP Server</h3>
            <p>
                本项目参加<strong>魔搭AI Hackathon 2025 - MCP Server开发赛道</strong><br/>
                支持MCP协议，可被Claude、GPT等AI助手直接调用<br/>
                <em>让AI助手拥有专业的产品开发规划能力</em>
            </p>
            <div style="margin-top: 15px;">
                <span style="background: #007bff; color: white; padding: 5px 15px; border-radius: 20px; margin: 0 5px;">MCP协议</span>
                <span style="background: #28a745; color: white; padding: 5px 15px; border-radius: 20px; margin: 0 5px;">AI驱动</span>
                <span style="background: #ffc107; color: black; padding: 5px 15px; border-radius: 20px; margin: 0 5px;">开源</span>
                <span style="background: #dc3545; color: white; padding: 5px 15px; border-radius: 20px; margin: 0 5px;">云部署</span>
            </div>
        </div>
        """)
        
        # 绑定事件
        generate_btn.click(
            fn=generate_development_plan,
            inputs=[idea_input],
            outputs=[plan_output],
            api_name="generate_plan"
        )
        
        analyze_btn.click(
            fn=analyze_project_feasibility,
            inputs=[project_desc, budget_input, timeline_input],
            outputs=[analysis_output],
            api_name="analyze_feasibility"
        )
    
    return demo

# 启动应用
if __name__ == "__main__":
    demo = create_modern_ui()
    
    # 检测运行环境
    is_modelscope = "MODELSCOPE" in os.environ or os.environ.get("MODELSCOPE_ENVIRONMENT") == "studio"
    
    try:
        if is_modelscope:
            # ModelScope环境：启用MCP Server模式
            logger.info("ModelScope环境启动，支持MCP协议...")
            demo.launch(
                server_name="0.0.0.0",
                server_port=7860,
                share=False,
                quiet=True,
                show_error=False,
                mcp_server=True,  # 关键：启用MCP Server模式
                max_threads=4
            )
        else:
            # 本地环境
            logger.info("本地环境启动...")
            demo.launch(
                server_name="127.0.0.1",
                server_port=7860,
                share=True,
                mcp_server=True  # 本地也支持MCP
            )
            
    except Exception as e:
        logger.error(f"启动失败: {e}")
        # 降级启动
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            quiet=True,
            mcp_server=True
        )