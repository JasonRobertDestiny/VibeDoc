import gradio as gr
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_function(text):
    logger.info(f"测试函数被调用，输入: {text}")
    if not text:
        return "请输入一些文本！"
    return f"✅ 收到输入: {text}"

# 创建简单的测试界面
with gr.Blocks() as demo:
    gr.Markdown("# 测试界面")
    
    with gr.Row():
        input_box = gr.Textbox(label="输入测试文本", placeholder="输入一些内容...")
        submit_btn = gr.Button("提交", variant="primary")
    
    output_box = gr.Markdown(label="输出结果")
    
    submit_btn.click(
        fn=test_function,
        inputs=input_box,
        outputs=output_box
    )

if __name__ == "__main__":
    logger.info("启动测试应用...")
    demo.launch(
        server_name="0.0.0.0",
        server_port=7861,
        share=False
    )
