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
    基于用户创意生成完整的产品开发计划，包括技术方案、部署策略和推广方案。
    
    Args:
        user_idea (str): 用户的产品创意描述，可以是任何类型的应用或服务想法
        
    Returns:
        str: 结构化的Markdown格式开发计划，包含产品分析、技术栈推荐、开发步骤、部署方案和推广策略
    """
    if not user_idea or not user_idea.strip():
        return "❌ 请输入您的产品创意！"
        
    if not API_KEY:
        return "❌ 错误：未配置API密钥"

    prompt = f"""你是一位资深的产品经理和全栈开发专家。基于用户想法生成专业的开发计划。

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

    try:
        response = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "Qwen/Qwen2.5-72B-Instruct",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 3000,
                "temperature": 0.7
            },
            timeout=60
        )
        
        if response.status_code == 200:
            content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            return content if content else "❌ API返回空内容"
        else:
            return f"❌ API请求失败: HTTP {response.status_code}"
            
    except Exception as e:
        return f"❌ 处理错误: {str(e)}"

def copy_to_clipboard(text):
    """复制文本到剪贴板的JavaScript函数"""
    return f"""
    <script>
    function copyToClipboard() {{
        const text = `{text.replace('`', '\\`')}`;
        navigator.clipboard.writeText(text).then(function() {{
            alert('✅ 已复制到剪贴板！');
        }}, function(err) {{
            console.error('复制失败: ', err);
            alert('❌ 复制失败，请手动复制');
        }});
    }}
    copyToClipboard();
    </script>
    """

def download_as_file(content, filename, format_type):
    """生成下载链接"""
    if format_type == "markdown":
        content_type = "text/markdown"
        extension = ".md"
    elif format_type == "txt":
        content_type = "text/plain"
        extension = ".txt"
    elif format_type == "json":
        content_type = "application/json"
        extension = ".json"
        # 将markdown转为JSON格式
        content = json.dumps({"title": filename, "content": content, "created_at": datetime.now().isoformat()}, ensure_ascii=False, indent=2)
    
    # 创建临时文件
    import tempfile
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=extension, delete=False, encoding='utf-8')
    temp_file.write(content)
    temp_file.close()
    
    return temp_file.name

# 自定义CSS
custom_css = """
.main-container {
    max-width: 1000px;
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

.action-buttons {
    display: flex;
    gap: 10px;
    margin-top: 15px;
    flex-wrap: wrap;
}

.btn-copy {
    background: #28a745;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
}

.btn-download {
    background: #007bff;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
}

.btn-copy:hover, .btn-download:hover {
    opacity: 0.8;
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
"""

# 创建Gradio界面
with gr.Blocks(
    title="VibeDoc - MCP开发计划生成器",
    theme=gr.themes.Soft(primary_hue="blue"),
    css=custom_css
) as demo:
    
    # 设置MCP服务器环境变量
    os.environ["GRADIO_MCP_SERVER"] = "True"
    
    gr.HTML("""
    <div class="header-gradient">
        <h1>🚀 VibeDoc - AI开发计划生成器</h1>
        <p style="font-size: 18px; margin: 15px 0; opacity: 0.95;">
            基于AI的产品开发计划生成工具，支持MCP协议
        </p>
        <p style="opacity: 0.85;">
            一键将创意转化为完整的开发方案，可被Claude等AI助手调用
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
                "🤖 AI生成开发计划",
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
            </div>
            """)
    
    # 结果显示区域
    with gr.Column(elem_classes="result-container"):
        plan_output = gr.Markdown(
            value="💭 **AI生成的完整开发计划将在这里显示...**\n\n点击上方按钮开始生成您的专属开发计划！",
            elem_id="plan_result"
        )
        
        # 操作按钮区域
        with gr.Row():
            copy_btn = gr.Button("📋 复制内容", size="sm", variant="secondary")
            download_md_btn = gr.Button("📥 下载 Markdown", size="sm", variant="secondary") 
            download_txt_btn = gr.Button("📄 下载 文本", size="sm", variant="secondary")
            download_json_btn = gr.Button("📦 下载 JSON", size="sm", variant="secondary")
        
        # 下载文件组件（隐藏）
        download_file = gr.File(visible=False)
    
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
    
    # 绑定事件
    def handle_generate(user_idea):
        result = generate_development_plan(user_idea)
        return result
    
    def handle_copy(plan_content):
        if plan_content and "AI生成的完整开发计划将在这里显示" not in plan_content:
            # 使用JavaScript复制到剪贴板
            return gr.update(), gr.HTML("""
            <script>
            navigator.clipboard.writeText(`""" + plan_content.replace('`', '\\`').replace('\n', '\\n') + """`).then(function() {
                alert('✅ 内容已复制到剪贴板！');
            });
            </script>
            """)
        return gr.update(), gr.update()
    
    def handle_download(plan_content, format_type):
        if plan_content and "AI生成的完整开发计划将在这里显示" not in plan_content:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"VibeDoc_开发计划_{timestamp}"
            
            try:
                temp_path = download_as_file(plan_content, filename, format_type)
                return gr.update(value=temp_path, visible=True)
            except Exception as e:
                logger.error(f"下载失败: {e}")
                return gr.update()
        return gr.update()
    
    # 绑定事件
    generate_btn.click(
        fn=handle_generate,
        inputs=[idea_input],
        outputs=[plan_output],
        api_name="generate_plan"
    )
    
    # 复制按钮（使用JavaScript）
    copy_btn.click(
        fn=lambda content: None,
        inputs=[plan_output],
        outputs=[],
        js="""
        function(content) {
            if (content && !content.includes('AI生成的完整开发计划将在这里显示')) {
                navigator.clipboard.writeText(content).then(function() {
                    alert('✅ 内容已复制到剪贴板！');
                }).catch(function(err) {
                    alert('❌ 复制失败，请手动复制');
                });
            } else {
                alert('⚠️ 请先生成开发计划');
            }
        }
        """
    )
    
    # 下载按钮
    download_md_btn.click(
        fn=lambda content: handle_download(content, "markdown"),
        inputs=[plan_output],
        outputs=[download_file]
    )
    
    download_txt_btn.click(
        fn=lambda content: handle_download(content, "txt"),
        inputs=[plan_output],
        outputs=[download_file]
    )
    
    download_json_btn.click(
        fn=lambda content: handle_download(content, "json"),
        inputs=[plan_output],
        outputs=[download_file]
    )

# 启动应用
if __name__ == "__main__":
    # 设置环境变量启用MCP
    os.environ["GRADIO_MCP_SERVER"] = "True"
    
    # 检测运行环境
    is_modelscope = "MODELSCOPE" in os.environ or os.environ.get("MODELSCOPE_ENVIRONMENT") == "studio"
    
    try:
        if is_modelscope:
            # ModelScope环境
            demo.launch(
                server_name="0.0.0.0",
                server_port=7860,
                share=False,
                quiet=True,
                show_error=False,
                max_threads=4
            )
        else:
            # 本地环境
            demo.launch(
                server_name="127.0.0.1",
                server_port=7860,
                share=True
            )
            
    except Exception as e:
        logger.error(f"启动失败: {e}")
        # 降级启动
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            quiet=True
        )