#!/usr/bin/env python3
"""
VibeDoc 启动脚本
用于ModelScope平台部署
"""

import os
import sys
import signal
import logging
from pathlib import Path

# 设置基础日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    """优雅关闭处理"""
    logger.info(f"收到信号 {signum}，正在优雅关闭...")
    sys.exit(0)

def main():
    """主启动函数"""
    try:
        # 注册信号处理器
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # 确保工作目录正确
        project_root = Path(__file__).parent
        os.chdir(project_root)
        
        logger.info("VibeDoc 启动中...")
        logger.info(f"工作目录: {os.getcwd()}")
        logger.info(f"Python版本: {sys.version}")
        
        # 导入并启动应用
        from app import demo
        
        # 启动Gradio应用
        demo.launch(
            server_name="0.0.0.0",
            server_port=int(os.environ.get("PORT", 7860)),
            share=False,
            inbrowser=False,
            quiet=False,
            show_error=True,
            enable_queue=True,
            max_threads=10
        )
        
    except KeyboardInterrupt:
        logger.info("收到键盘中断，正在退出...")
    except Exception as e:
        logger.error(f"启动失败: {e}")
        raise

if __name__ == "__main__":
    main()
