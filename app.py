import gradio as gr
import requests
import json
import os

# 设置API配置
API_KEY = os.getenv("SILICONFLOW_API_KEY")
API_URL = "https://api.siliconflow.cn/v1/chat/completions"

def generate_plan(idea):
    """调用AI API生成开发计划"""
    if not API_KEY:
        return "❌ 请设置 SILICONFLOW_API_KEY 环境变量"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    作为一个专业的技术顾问，请根据以下产品创意生成完整的开发计划：

    创意描述：{idea}

    请生成包含以下部分的详细开发计划：
    1. 产品概述
    2. 技术栈推荐
    3. 系统架构设计
    4. 开发计划
    5. 部署方案
    6. 营销策略
    7. AI编程助手提示词

    请用markdown格式输出，结构清晰，内容详细。
    """
    
    data = {
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 4000
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            return f"❌ API调用失败: {response.status_code}"
    except Exception as e:
        return f"❌ 错误: {str(e)}"

# 创建Gradio界面
with gr.Blocks(title="VibeDoc - AI驱动的开发计划生成器", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🚀 VibeDoc - AI驱动的开发计划生成器
    
    ### 🔥 一键将创意转化为完整开发方案！
    
    > 🏆 参赛项目 - 魔搭AI Hackathon 2025 - 赛道一：MCP Server开发赛道
    """)
    
    with gr.Row():
        with gr.Column(scale=1):
            idea_input = gr.Textbox(
                label="💡 输入您的产品创意",
                placeholder="例如：我想做一个在线协作文档工具，类似于腾讯文档...",
                lines=3
            )
            generate_btn = gr.Button("🚀 AI生成开发计划", variant="primary", size="lg")
            
            gr.Markdown("""
            ### 🎯 使用说明
            1. 在上方文本框中描述您的产品创意
            2. 点击"AI生成开发计划"按钮
            3. 等待30秒，获得完整的开发方案
            4. 结果包含技术栈、架构设计、部署方案等
            """)
        
        with gr.Column(scale=2):
            output = gr.Markdown(
                label="📋 生成的开发计划",
                value="请在左侧输入您的产品创意，然后点击生成按钮。"
            )
    
    # 绑定事件
    generate_btn.click(
        fn=generate_plan,
        inputs=[idea_input],
        outputs=[output]
    )
    
    gr.Markdown("""
    ---
    ### 🏗️ 技术架构
    - **前端**: Gradio Web界面
    - **AI服务**: Silicon Flow API (Qwen2.5-72B-Instruct)
    - **部署**: 魔塔ModelScope平台
    
    ### 📞 联系方式
    - **项目地址**: [GitHub - VibeDocs](https://github.com/JasonRobertDestiny/VibeDocs)
    - **赛道**: MCP Server开发赛道
    """)

if __name__ == "__main__":
    demo.launch()
