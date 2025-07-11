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

# 从环境变量中获取API密钥，如果没有则使用默认测试密钥（仅用于测试）
API_KEY = os.environ.get("SILICONFLOW_API_KEY", "sk-eeqxcykxvmomeunmpbbgdsqgvrxqksyapauxzexphsiflgsy")
API_URL = "https://api.siliconflow.cn/v1/chat/completions"

logger.info("VibeDoc应用启动中...")
logger.info(f"API密钥配置状态: {'已配置' if API_KEY else '未配置'}")

def generate_plan(user_idea):
    """
    接收用户想法，调用大模型API，并返回生成的开发计划。
    """
    logger.info(f"generate_plan函数被调用，输入长度: {len(user_idea) if user_idea else 0}")
    
    if not user_idea or not user_idea.strip():
        logger.warning("用户输入为空")
        return "❌ 请输入您的产品创意！"
        
    if not API_KEY:
        logger.error("API密钥未配置")
        return "❌ 错误：未配置SILICONFLOW_API_KEY环境变量。请在ModelScope Studio设置中添加。"

    logger.info("开始调用AI API...")

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
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "messages": [
            {
                "role": "user",
                "content": master_prompt
            }
        ],
        "max_tokens": 2500,  # 减少token数量以提高稳定性
        "temperature": 0.7,
        "stream": False
    }

    try:
        logger.info("正在调用Silicon Flow API...")
        response = requests.post(API_URL, headers=headers, json=payload, timeout=45)  # 减少超时时间
        
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
with gr.Blocks(theme=gr.themes.Default(primary_hue="blue", secondary_hue="blue")) as demo:
    gr.Markdown(
        """
        # 🚀 VibeDoc - AI驱动的开发计划生成器
        一键将创意转化为完整的开发方案！参赛魔搭AI Hackathon 2025 (MCP Server开发赛道)。
        
        **✨ 功能特色：**
        - 🤖 基于Qwen2.5-72B-Instruct大模型
        - 📋 生成完整的开发计划和技术方案
        - 🔧 支持MCP Server协议
        - 🚀 一键部署到ModelScope平台
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
            
            submit_button = gr.Button("🤖 AI生成开发计划", variant="primary", size="lg")
    
    with gr.Row():
        plan_output = gr.Markdown(
            label="生成的开发计划",
            value="📝 AI生成的开发计划将在这里显示..."
        )

    # 绑定按钮点击事件
    def handle_submit(user_idea):
        logger.info(f"🔥 按钮点击事件触发！用户输入: {user_idea[:50] if user_idea else 'None'}...")
        try:
            if not user_idea or not user_idea.strip():
                logger.warning("用户输入为空")
                return "❌ 请输入您的产品创意！"
            
            logger.info("开始调用generate_plan函数...")
            result = generate_plan(user_idea)
            logger.info(f"✅ 处理完成，结果长度: {len(result) if result else 0}")
            return result
        except Exception as e:
            logger.error(f"❌ 处理过程中发生错误: {e}")
            return f"❌ 处理过程中发生错误: {str(e)}"

    submit_button.click(
        fn=handle_submit,
        inputs=[idea_input],
        outputs=[plan_output],
        api_name="generate_development_plan"
    )
    
    # 添加示例
    gr.Examples(
        examples=[
            ["我想做一个帮助用户记录每天喝水量的App"],
            ["开发一个在线代码编辑器，支持多种编程语言"],
            ["创建一个基于AI的智能客服系统"],
            ["制作一个任务管理和番茄钟结合的生产力工具"]
        ],
        inputs=[idea_input],
        label="💡 点击示例快速开始"
    )

# 启动Gradio应用
if __name__ == "__main__":
    try:
        # 检测运行环境
        is_modelscope = os.environ.get("MODELSCOPE_ENVIRONMENT") == "studio" or "MODELSCOPE" in os.environ
        is_local = not is_modelscope
        
        if is_modelscope:
            # ModelScope环境：使用简化配置
            logger.info("检测到ModelScope环境，使用优化配置...")
            demo.launch(
                server_name="0.0.0.0",
                server_port=7860,
                share=False,
                quiet=True,  # 减少日志输出
                show_error=False,  # 避免错误显示导致的问题
                enable_queue=False,  # 禁用队列以减少资源使用
                max_threads=2  # 限制线程数
            )
        else:
            # 本地环境：完整配置
            logger.info("本地环境启动...")
            demo.launch(
                server_name="127.0.0.1",
                server_port=7860,
                share=False,
                quiet=False,
                show_error=True
            )
            
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        # 最简配置降级启动
        try:
            logger.info("尝试使用最简配置启动...")
            demo.launch(
                server_name="0.0.0.0",
                server_port=7860,
                quiet=True
            )
        except Exception as e2:
            logger.error(f"最简配置启动也失败: {e2}")
            raise
