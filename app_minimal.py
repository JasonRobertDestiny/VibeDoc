import gradio as gr
import requests
import os
import json
import logging
import sys
import gc

# 配置最简日志
logging.basicConfig(
    level=logging.WARNING,  # 减少日志输出
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API配置
API_KEY = os.environ.get("SILICONFLOW_API_KEY", "sk-eeqxcykxvmomeunmpbbgdsqgvrxqksyapauxzexphsiflgsy")
API_URL = "https://api.siliconflow.cn/v1/chat/completions"

def generate_plan(user_idea):
    """生成开发计划"""
    if not user_idea or not user_idea.strip():
        return "❌ 请输入您的产品创意！"
        
    if not API_KEY:
        return "❌ 错误：未配置API密钥"

    # 简化的提示词
    master_prompt = f"""基于以下用户想法，生成一份结构化的开发计划：

用户想法：{user_idea}

请按以下格式回复：
# 产品概述
# 技术方案  
# 开发计划
# 部署建议
# 推广策略

保持简洁实用。"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "messages": [{"role": "user", "content": master_prompt}],
        "max_tokens": 2000,
        "temperature": 0.7,
        "stream": False
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            return f"❌ API请求失败: {response.status_code}"
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # 手动垃圾回收
        del data, response
        gc.collect()
        
        return content if content else "❌ API返回空内容"
        
    except Exception as e:
        return f"❌ 处理错误: {str(e)}"

# 创建简化界面
def create_app():
    with gr.Blocks(title="VibeDoc") as demo:
        gr.Markdown("# 🚀 VibeDoc - AI开发计划生成器")
        
        with gr.Row():
            idea_input = gr.Textbox(
                label="💡 输入您的产品创意",
                lines=3,
                placeholder="例如：我想做一个帮助用户记录每天喝水量的App..."
            )
        
        with gr.Row():
            submit_button = gr.Button("🤖 生成开发计划", variant="primary")
        
        with gr.Row():
            plan_output = gr.Markdown(label="开发计划")

        def handle_click(user_idea):
            try:
                result = generate_plan(user_idea)
                return result
            except Exception as e:
                return f"❌ 处理错误: {str(e)}"

        submit_button.click(
            fn=handle_click,
            inputs=[idea_input],
            outputs=[plan_output]
        )
        
        # 简单示例
        gr.Examples(
            examples=[
                ["我想做一个帮助用户记录每天喝水量的App"],
                ["开发一个在线代码编辑器"]
            ],
            inputs=[idea_input]
        )

    return demo

if __name__ == "__main__":
    try:
        demo = create_app()
        
        # 最简启动配置
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            quiet=True,
            show_error=False,
            enable_queue=False,
            max_threads=1
        )
        
    except Exception as e:
        logger.error(f"启动失败: {e}")
        # 超简启动
        try:
            demo = create_app()
            demo.launch()
        except Exception as e2:
            print(f"完全启动失败: {e2}")
            raise
