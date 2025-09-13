"""
直接MCP客户端 - 用于魔塔环境绕过Node.js Bridge
支持直接调用MCP服务的SSE端点
"""

import requests
import json
import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DirectMCPResult:
    """直接MCP调用结果"""
    success: bool
    data: str
    service_name: str
    execution_time: float
    error_message: Optional[str] = None

class DirectMCPClient:
    """直接MCP客户端 - 用于魔塔环境"""
    
    def __init__(self):
        self.timeout = 30
        
    def call_mcp_service(
        self, 
        service_url: str, 
        service_name: str,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> DirectMCPResult:
        """
        直接调用MCP服务
        """
        start_time = time.time()
        
        try:
            logger.info(f"🔗 直接调用 {service_name} - {tool_name}")
            logger.info(f"📡 服务URL: {service_url}")
            
            # 构造MCP请求
            mcp_request = {
                "jsonrpc": "2.0",
                "id": int(time.time() * 1000),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": tool_args
                }
            }
            
            # 发送请求
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            response = requests.post(
                service_url,
                json=mcp_request,
                headers=headers,
                timeout=self.timeout
            )
            
            execution_time = time.time() - start_time
            
            logger.info(f"📊 {service_name} 响应状态: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                if "result" in result:
                    content = result["result"].get("content", [])
                    if content and len(content) > 0:
                        data = content[0].get("text", "")
                        logger.info(f"✅ {service_name} 调用成功")
                        return DirectMCPResult(
                            success=True,
                            data=data,
                            service_name=service_name,
                            execution_time=execution_time
                        )
                
                # 检查错误
                if "error" in result:
                    error_msg = result["error"].get("message", "未知错误")
                    logger.error(f"❌ {service_name} 返回错误: {error_msg}")
                    return DirectMCPResult(
                        success=False,
                        data="",
                        service_name=service_name,
                        execution_time=execution_time,
                        error_message=error_msg
                    )
                
                logger.warning(f"⚠️ {service_name} 返回空结果")
                return DirectMCPResult(
                    success=False,
                    data="",
                    service_name=service_name,
                    execution_time=execution_time,
                    error_message="服务返回空结果"
                )
            
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"❌ {service_name} 调用失败: {error_msg}")
                return DirectMCPResult(
                    success=False,
                    data="",
                    service_name=service_name,
                    execution_time=execution_time,
                    error_message=error_msg
                )
                
        except requests.exceptions.Timeout:
            execution_time = time.time() - start_time
            error_msg = f"服务调用超时 ({self.timeout}s)"
            logger.error(f"⏱️ {service_name} {error_msg}")
            return DirectMCPResult(
                success=False,
                data="",
                service_name=service_name,
                execution_time=execution_time,
                error_message=error_msg
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"调用异常: {str(e)}"
            logger.error(f"💥 {service_name} {error_msg}")
            return DirectMCPResult(
                success=False,
                data="",
                service_name=service_name,
                execution_time=execution_time,
                error_message=error_msg
            )

# 全局实例
direct_mcp_client = DirectMCPClient()