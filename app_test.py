import gradio as gr
import requests
import os
import json
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 直接设置API密钥用于测试
API_KEY = "sk-eeqxcykxvmomeunmpbbgdsqgvrxqksyapauxzexphsiflgsy"
API_URL = "https://api.siliconflow.cn/v1/chat/completions"

logger.info("VibeDoc测试版启动中...")
logger.info(f"API密钥配置状态: {'已配置' if API_KEY else '未配置'}")

def generate_plan(user_idea):
    """
    接收用户想法，调用大模型API，并返回生成的开发计划。
    """
    logger.info(f"generate_plan函数被调用，输入长度: {len(user_idea) if user_idea else 0}")
    
    if not user_idea or not user_idea.strip():
        logger.warning("用户输入为空")
        return "❌ 请输入您的产品创意！"

    logger.info("开始调用AI API...")

    # 简化的提示词用于测试
    master_prompt = f"""请基于以下用户想法，生成一份结构化的开发计划：

用户想法：{user_idea}

请按以下格式回复：
# 产品概述
# 技术方案
# 开发计划
# 部署建议

保持简洁但详细。"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "messages": [
            {
                "role": "user",
                "content": master_prompt
            }
        ],
        "max_tokens": 2000,
        "temperature": 0.7,
        "stream": False
    }

    try:
        logger.info("正在调用Silicon Flow API...")
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        
        if response.status_code != 200:
            error_detail = f"状态码: {response.status_code}"
            try:
                error_json = response.json()
                error_detail += f", 错误详情: {error_json}"
            except:
                error_detail += f", 响应内容: {response.text[:500]}"
            logger.error(f"API请求失败: {error_detail}")
            return f"❌ API请求失败: {error_detail}"
        
        data = response.json()
        generated_content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        if not generated_content:
            logger.error(f"API返回空内容: {data}")
            return f"❌ API返回了空内容，请稍后重试"
            
        logger.info("✅ 开发计划生成成功")
        return generated_content
        
    except requests.exceptions.Timeout:
        logger.error("API请求超时")
        return "❌ 请求超时，请稍后重试"
    except requests.exceptions.RequestException as e:
        logger.error(f"网络请求失败: {e}")
        return f"❌ 网络请求失败：{str(e)}"
    except Exception as e:
        logger.error(f"处理时发生未知错误: {e}")
        return f"❌ 处理时发生错误：{str(e)}"

# 创建Gradio界面
def create_interface():
    with gr.Blocks(
        theme=gr.themes.Default(primary_hue="blue", secondary_hue="blue"),
        title="VibeDoc - AI开发计划生成器"
    ) as demo:
        gr.Markdown(
            """
            # 🚀 VibeDoc - AI驱动的开发计划生成器
            一键将创意转化为完整的开发方案！参赛魔搭AI Hackathon 2025 (MCP Server开发赛道)。
            
            **使用说明：**
            1. 在下方文本框中输入您的产品创意
            2. 点击"AI生成开发计划"按钮
            3. 等待AI为您生成详细的开发计划
            """
        )
        
        with gr.Row():
            with gr.Column():
                idea_input = gr.Textbox(
                    label="💡 输入您的产品创意",
                    placeholder="例如：我想做一个帮助用户记录每天喝水量的App...",
                    lines=4,
                    max_lines=10
                )
                
                submit_button = gr.Button(
                    "🤖 AI生成开发计划", 
                    variant="primary",
                    size="lg"
                )
        
        with gr.Row():
            plan_output = gr.Markdown(
                label="生成的开发计划",
                value="📝 AI生成的开发计划将在这里显示..."
            )

        # 绑定按钮点击事件
        def handle_click(user_idea):
            logger.info(f"按钮点击事件触发，用户输入: {user_idea[:50] if user_idea else 'None'}...")
            try:
                result = generate_plan(user_idea)
                logger.info("处理完成，返回结果")
                return result
            except Exception as e:
                logger.error(f"处理过程中发生错误: {e}")
                return f"❌ 处理过程中发生错误: {str(e)}"

        submit_button.click(
            fn=handle_click,
            inputs=[idea_input],
            outputs=[plan_output],
            api_name="generate_development_plan"
        )
        
        # 添加示例
        gr.Examples(
            examples=[
                ["我想做一个帮助用户记录每天喝水量的App"],
                ["开发一个在线代码编辑器，支持多种编程语言"],
                ["创建一个基于AI的智能客服系统"]
            ],
            inputs=[idea_input]
        )

    return demo

# 启动应用
if __name__ == "__main__":
    try:
        # 设置环境变量以启用MCP服务器
        os.environ["GRADIO_MCP_SERVER"] = "True"
        logger.info("启动VibeDoc测试版，MCP服务器已启用...")
        
        demo = create_interface()
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            quiet=False,
            show_error=True,
            mcp_server=True
        )
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        raise
