import gradio as gr
import requests
import os
import json

# 从环境变量中获取API密钥
API_KEY = os.environ.get("SILICONFLOW_API_KEY")
API_URL = "https://api.siliconflow.cn/v1/chat/completions"

def generate_plan(user_idea):
    """
    接收用户想法，调用大模型API，并返回生成的开发计划。
    """
    if not API_KEY:
        return "错误：未配置SILICONFLOW_API_KEY环境变量。请在创空间设置中添加。"

    # 这里是我们之前设计的"总指令 (Master Prompt)"
    master_prompt = f"""# 角色与目标
你是一位经验丰富的互联网产品经理和全栈开发技术专家。你的任务是基于用户提供的一个初步想法，进行深度思考和扩展，并生成一份专业、完整、结构化的初步开发计划。

# 用户想法
{user_idea}

# 你的任务与输出要求
你的回答必须是一份格式优美的Markdown文档。文档应该包含以下部分，每个部分都应有详细且专业的内容：
1.  **确定要做什么**: (分析痛点、相关热词、成功案例)
2.  **确定产品名称**: (提出产品名、域名建议、品牌概念)
3.  **把产品做出来**: (推荐技术栈、部署方案、开发计划、设计系统)
4.  **部署上线**: (托管平台、域名配置、SSL证书、性能优化)
5.  **推广宣传**: (社交媒体策略、产品发布、内容营销、社区建设)
6.  **数据分析**: (分析工具、关键指标、用户行为分析、性能监控)
7.  **运营迭代**: (用户反馈、产品迭代、营销优化、商业模式)

同时，在文档的末尾，请附上一个"AI编程助手提示词"部分，将上述计划分解成可以一步步执行的、清晰的编程任务。
"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "deepseek-ai/DeepSeek-V2",
        "messages": [
            {
                "role": "user",
                "content": master_prompt
            }
        ]
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        generated_content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return generated_content
    except requests.exceptions.RequestException as e:
        return f"API请求失败: {e}"
    except Exception as e:
        return f"处理时发生未知错误: {e}"

# 创建Gradio界面
with gr.Blocks(theme=gr.themes.Default(primary_hue="blue", secondary_hue="blue")) as demo:
    gr.Markdown(
        """
        # 🚀 VibeDoc - AI驱动的开发计划生成器
        一键将创意转化为完整的开发方案！参赛魔搭AI Hackathon 2025 (MCP Server开发赛道)。
        """
    )
    
    with gr.Row():
        with gr.Column():
            idea_input = gr.Textbox(
                label="💡 输入您的产品创意",
                placeholder="例如：我想做一个帮助用户记录每天喝水量的App...",
                lines=3
            )
            
            submit_button = gr.Button("🤖 AI生成开发计划", variant="primary")
    
    with gr.Row():
        plan_output = gr.Markdown(label="生成的开发计划")

    submit_button.click(
        fn=generate_plan,
        inputs=idea_input,
        outputs=plan_output
    )

# 启动Gradio应用，并开启MCP Server功能
if __name__ == "__main__":
    demo.launch(mcp_server=True)