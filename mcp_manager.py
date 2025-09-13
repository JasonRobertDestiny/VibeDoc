"""
MCP服务管理器 - 修复版本
支持魔塔环境的直接MCP调用和本地Node.js桥接
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import requests
from urllib.parse import urlparse
import subprocess
import threading

from config import config, MCPServiceConfig
from mcp_direct_client import direct_mcp_client, DirectMCPResult

logger = logging.getLogger(__name__)

class MCPServiceType(Enum):
    """MCP服务类型枚举"""
    DEEPWIKI = "deepwiki"
    FETCH = "fetch"

@dataclass
class MCPCallResult:
    """MCP调用结果"""
    success: bool
    data: str
    service_name: str
    execution_time: float
    error_message: Optional[str] = None

class MCPBridgeService:
    """MCP桥接服务管理"""
    
    def __init__(self):
        self.bridge_port = int(os.getenv('MCP_BRIDGE_PORT', 3003))
        self.bridge_url = f"http://localhost:{self.bridge_port}"
        self.bridge_process = None
        self.is_starting = False
        
    def start_bridge_service(self):
        """启动Node.js桥接服务"""
        if self.is_starting:
            return
            
        self.is_starting = True
        
        try:
            # 检查服务是否已经运行
            if self.is_bridge_running():
                logger.info("✅ MCP桥接服务已在运行")
                self.is_starting = False
                return
            
            logger.info("🚀 启动MCP桥接服务...")
            
            # 检查Node.js和npm是否可用
            try:
                subprocess.run(['node', '--version'], capture_output=True, check=True)
                subprocess.run(['npm', '--version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.error("❌ Node.js或npm未安装，无法启动MCP桥接服务")
                self.is_starting = False
                return
            
            # 安装依赖
            bridge_dir = os.path.join(os.path.dirname(__file__), 'mcp_bridge')
            if not os.path.exists(os.path.join(bridge_dir, 'node_modules')):
                logger.info("📦 安装MCP桥接服务依赖...")
                try:
                    subprocess.run(['npm', 'install'], cwd=bridge_dir, check=True, capture_output=True)
                except subprocess.CalledProcessError as e:
                    logger.error(f"❌ npm install失败: {e}")
                    self.is_starting = False
                    return
            
            # 启动服务
            def start_service():
                try:
                    self.bridge_process = subprocess.Popen(
                        ['node', 'index.js'],
                        cwd=bridge_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    logger.info("✅ MCP桥接服务启动成功")
                except Exception as e:
                    logger.error(f"❌ MCP桥接服务启动失败: {e}")
            
            # 在后台线程启动
            threading.Thread(target=start_service, daemon=True).start()
            
            # 等待服务启动
            for i in range(10):
                time.sleep(1)
                if self.is_bridge_running():
                    logger.info("✅ MCP桥接服务启动完成")
                    break
            else:
                logger.warning("⚠️ MCP桥接服务启动超时")
                
        except Exception as e:
            logger.error(f"❌ 启动MCP桥接服务失败: {e}")
        finally:
            self.is_starting = False
    
    def is_bridge_running(self) -> bool:
        """检查桥接服务是否运行"""
        try:
            response = requests.get(f"{self.bridge_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def stop_bridge_service(self):
        """停止桥接服务"""
        if self.bridge_process:
            self.bridge_process.terminate()
            self.bridge_process = None
            logger.info("🛑 MCP桥接服务已停止")

class MCPServiceManager:
    """MCP服务管理器 - 支持魔塔环境和本地环境"""
    
    def __init__(self):
        self.services = config.mcp_services
        self.call_history: List[MCPCallResult] = []
        self.service_stats = {
            service_key: {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "average_response_time": 0.0,
                "last_call_time": None
            }
            for service_key in self.services.keys()
        }
        self.bridge = MCPBridgeService()
        
        # 检测环境
        self.is_modelspace = os.getenv('MODELSCOPE_ENVIRONMENT') or os.getenv('SPACE_ID')
        
        # 本地环境启动桥接服务
        if not self.is_modelspace:
            self.bridge.start_bridge_service()
            
        logger.info(f"🏗️ MCP服务管理器初始化完成 ({'魔塔直连' if self.is_modelspace else 'Node.js桥接'}模式)")
    
    def get_service_for_url(self, url: str) -> List[MCPServiceType]:
        """根据URL智能选择MCP服务"""
        if not url:
            return []
        
        services = []
        url_lower = url.lower()
        
        # DeepWiki服务路由规则
        if "deepwiki.org" in url_lower:
            services.append(MCPServiceType.DEEPWIKI)
        
        # GitHub项目需要多服务协作
        elif "github.com" in url_lower:
            services.append(MCPServiceType.FETCH)
            # 如果是教育、健康、金融等相关项目，也调用DeepWiki
            if any(keyword in url_lower for keyword in [
                "education", "health", "finance", "learning", "medical", 
                "investment", "fitness", "diet", "blockchain", "web3",
                "ethereum", "solidity", "smart-contract", "defi", "nft"
            ]):
                services.append(MCPServiceType.DEEPWIKI)
        
        # 权威机构网站优先使用Fetch服务
        elif any(domain in url_lower for domain in [
            "who.int", "cdc.gov", "nih.gov", "edu", "gov", 
            "wikipedia.org", "stackoverflow.com", "medium.com"
        ]):
            services.append(MCPServiceType.FETCH)
        
        # 通用网页使用Fetch服务
        else:
            services.append(MCPServiceType.FETCH)
        
        # 过滤只返回已启用的服务
        return [s for s in services if self.services[s.value].enabled]
    
    def call_single_mcp_service(
        self, 
        service_type: MCPServiceType, 
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> MCPCallResult:
        """调用单个MCP服务 - 支持魔塔直连和本地桥接"""
        start_time = time.time()
        service_config = self.services[service_type.value]
        
        if not service_config.enabled:
            return MCPCallResult(
                success=False,
                data="",
                service_name=service_config.name,
                execution_time=0.0,
                error_message="服务未启用"
            )
        
        # 检查是否跳过MCP服务
        skip_mcp = os.getenv("SKIP_MCP", "false").lower() == "true"
        if skip_mcp:
            return MCPCallResult(
                success=False,
                data="",
                service_name=service_config.name,
                execution_time=0.0,
                error_message="MCP服务已被跳过 (SKIP_MCP=true)"
            )
        
        try:
            logger.info(f"🔥 调用 {service_config.name} 工具: {tool_name}")
            logger.info(f"🔥 参数: {json.dumps(tool_args, ensure_ascii=False, indent=2)}")
            
            # 魔塔环境：使用直接调用
            if self.is_modelspace:
                logger.info("🏠 魔塔环境，使用直接MCP调用")
                direct_result = direct_mcp_client.call_mcp_service(
                    service_config.url,
                    service_config.name,
                    tool_name,
                    tool_args
                )
                
                # 转换直接调用结果为标准结果
                result = MCPCallResult(
                    success=direct_result.success,
                    data=direct_result.data,
                    service_name=direct_result.service_name,
                    execution_time=direct_result.execution_time,
                    error_message=direct_result.error_message
                )
                
                self._update_service_stats(service_type, result.success, result.execution_time)
                if result.success:
                    logger.info(f"✅ 魔塔直接MCP调用成功，内容长度: {len(result.data)} 字符")
                else:
                    logger.warning(f"⚠️ 魔塔直接MCP调用失败: {result.error_message}")
                
                return result
            
            # 本地环境：使用Node.js桥接
            else:
                logger.info("💻 本地环境，使用Node.js桥接服务")
                # 确保桥接服务运行
                if not self.bridge.is_bridge_running():
                    logger.info("🔄 桥接服务未运行，尝试启动...")
                    self.bridge.start_bridge_service()
                    time.sleep(2)
                    
                    if not self.bridge.is_bridge_running():
                        raise Exception("桥接服务启动失败")
                
                # 通过桥接服务调用MCP
                payload = {
                    "url": service_config.url,
                    "toolName": tool_name,
                    "arguments": tool_args,
                    "config": {
                        "headers": {"Authorization": f"Bearer {service_config.api_key}"} if service_config.api_key else {}
                    }
                }
                
                response = requests.post(
                    f"{self.bridge.bridge_url}/call-tool",
                    json=payload,
                    timeout=30
                )
                
                execution_time = time.time() - start_time
                
                logger.info(f"🔥 桥接服务响应状态: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("success") and data.get("data"):
                        content = self._extract_content_from_mcp_result(data["data"])
                        
                        if content and len(str(content).strip()) > 10:
                            result = MCPCallResult(
                                success=True,
                                data=str(content),
                                service_name=service_config.name,
                                execution_time=execution_time
                            )
                            self._update_service_stats(service_type, True, execution_time)
                            logger.info(f"✅ 本地桥接MCP调用成功，内容长度: {len(str(content))} 字符")
                            return result
                    
                    error_msg = data.get("error", "未知错误")
                    logger.warning(f"⚠️ {service_config.name} 桥接MCP调用失败: {error_msg}")
                    result = MCPCallResult(
                        success=False,
                        data="",
                        service_name=service_config.name,
                        execution_time=execution_time,
                        error_message=error_msg
                    )
                    self._update_service_stats(service_type, False, execution_time)
                    return result
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.error(f"❌ {service_config.name} 桥接服务调用失败: {error_msg}")
                    result = MCPCallResult(
                        success=False,
                        data="",
                        service_name=service_config.name,
                        execution_time=execution_time,
                        error_message=error_msg
                    )
                    self._update_service_stats(service_type, False, execution_time)
                    return result
                    
        except requests.exceptions.Timeout:
            execution_time = time.time() - start_time
            error_msg = f"调用超时 (30秒)"
            logger.error(f"⏰ {service_config.name} {error_msg}")
            result = MCPCallResult(
                success=False,
                data="",
                service_name=service_config.name,
                execution_time=execution_time,
                error_message=error_msg
            )
            self._update_service_stats(service_type, False, execution_time)
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"调用异常: {str(e)}"
            logger.error(f"💥 {service_config.name} {error_msg}")
            result = MCPCallResult(
                success=False,
                data="",
                service_name=service_config.name,
                execution_time=execution_time,
                error_message=error_msg
            )
            self._update_service_stats(service_type, False, execution_time)
            return result
    
    def _extract_content_from_mcp_result(self, mcp_result: Any) -> Optional[str]:
        """从MCP调用结果中提取内容"""
        try:
            # MCP工具调用的标准响应格式
            if isinstance(mcp_result, dict):
                # 检查content字段
                if "content" in mcp_result:
                    content = mcp_result["content"]
                    if isinstance(content, list) and len(content) > 0:
                        # 处理内容数组
                        texts = []
                        for item in content:
                            if isinstance(item, dict) and "text" in item:
                                texts.append(item["text"])
                            elif isinstance(item, str):
                                texts.append(item)
                        return "\n".join(texts)
                    elif isinstance(content, str):
                        return content
                
                # 检查其他可能的字段
                for key in ["result", "data", "text", "message"]:
                    if key in mcp_result and mcp_result[key]:
                        return str(mcp_result[key])
            
            # 如果是字符串，直接返回
            if isinstance(mcp_result, str):
                return mcp_result
            
            # 其他情况，转换为字符串
            return str(mcp_result) if mcp_result else None
            
        except Exception as e:
            logger.error(f"💥 提取MCP结果内容失败: {e}")
            return str(mcp_result) if mcp_result else None
    
    def _update_service_stats(self, service_type: MCPServiceType, success: bool, execution_time: float):
        """更新服务统计信息"""
        stats = self.service_stats[service_type.value]
        stats["total_calls"] += 1
        stats["last_call_time"] = time.time()
        
        if success:
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1
        
        # 更新平均响应时间
        stats["average_response_time"] = (
            stats["average_response_time"] * (stats["total_calls"] - 1) + execution_time
        ) / stats["total_calls"]
    
    def fetch_knowledge_from_url(self, url: str) -> Tuple[bool, str]:
        """从URL获取知识 - 支持魔塔和本地环境"""
        if not url or not url.strip():
            return False, ""
        
        url = url.strip()
        
        # 检查是否暂时跳过MCP服务
        skip_mcp = os.getenv("SKIP_MCP", "false").lower() == "true"
        if skip_mcp:
            logger.info("🔄 跳过MCP服务调用 (SKIP_MCP=true)")
            return False, f"""
## 🔗 参考链接处理说明

**📍 提供的链接**: {url}

**🎯 处理方式**: 直接AI分析模式 (MCP服务已暂时禁用)

**🤖 AI处理**: 将基于创意内容和链接信息进行智能分析

**💡 说明**: 为确保系统稳定性，当前暂时禁用了外部MCP服务，AI会基于以下方式生成方案：
- ✅ 基于创意描述进行深度分析  
- ✅ 结合行业最佳实践
- ✅ 提供完整的技术方案
- ✅ 生成实用的编程提示词

**🔧 技术说明**: 如需启用MCP服务，请在环境变量中设置 `SKIP_MCP=false`

---
"""
        
        # 验证URL格式
        try:
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                return False, "❌ 无效的URL格式"
        except Exception:
            return False, "❌ URL解析失败"
        
        # 获取适合的MCP服务
        suitable_services = self.get_service_for_url(url)
        
        if not suitable_services:
            return False, "❌ 没有可用的MCP服务处理此URL"
        
        knowledge_sources = []
        successful_calls = 0
        
        # 调用MCP服务获取内容
        for service_type in suitable_services:
            tool_name, tool_args = self._build_tool_call_for_service(service_type, url)
            result = self.call_single_mcp_service(service_type, tool_name, tool_args)
            
            self.call_history.append(result)
            
            if result.success:
                successful_calls += 1
                knowledge_sources.append({
                    "service": result.service_name,
                    "content": result.data,
                    "execution_time": result.execution_time
                })
            else:
                logger.warning(f"⚠️ {result.service_name} 调用失败: {result.error_message}")
        
        # 整合结果
        if knowledge_sources:
            combined_knowledge = self._combine_knowledge_sources(url, knowledge_sources)
            return True, combined_knowledge
        else:
            return False, f"❌ 所有MCP服务调用失败，尝试了 {len(suitable_services)} 个服务"
    
    def _build_tool_call_for_service(self, service_type: MCPServiceType, url: str) -> Tuple[str, Dict[str, Any]]:
        """为不同的MCP服务构建工具调用"""
        if service_type == MCPServiceType.DEEPWIKI:
            return "fetch_content", {
                "url": url,
                "mode": "aggregate"
            }
        elif service_type == MCPServiceType.FETCH:
            return "fetch", {
                "url": url
            }
        else:
            return "fetch", {"url": url}
    
    def _combine_knowledge_sources(self, url: str, sources: List[Dict]) -> str:
        """整合多个知识源"""
        if not sources:
            return ""
        
        mode = "魔塔直连" if self.is_modelspace else "本地桥接"
        
        if len(sources) == 1:
            source = sources[0]
            return f"📖 **{source['service']}** ({mode}模式)：\n\n{source['content']}"
        
        # 多源整合
        fusion_header = f"""
## 🧠 多源知识融合 ({len(sources)}个知识源) - {mode}模式

**🔗 原始链接：** {url}

**🎯 MCP服务协作：** 使用{'魔塔直连' if self.is_modelspace else '本地Node.js桥接'}整合以下知识源

---

"""
        
        source_contents = []
        for i, source in enumerate(sources, 1):
            execution_time_str = f"({source['execution_time']:.2f}s)"
            source_content = f"""
### 📋 {i}. {source['service']} {execution_time_str}

{source['content']}

---
"""
            source_contents.append(source_content)
        
        return fusion_header + "\n".join(source_contents)
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取所有MCP服务健康状态"""
        status = {}
        
        for service_key, service_config in self.services.items():
            if not service_config.enabled:
                status[service_key] = {
                    "name": service_config.name,
                    "status": "disabled",
                    "enabled": False
                }
                continue
            
            # 检查服务状态
            if self.is_modelspace:
                # 魔塔环境直接检查
                service_status = "healthy"  # 魔塔环境假设可用
            else:
                # 本地环境检查桥接服务状态
                service_status = "healthy" if self.bridge.is_bridge_running() else "unhealthy"
            
            status[service_key] = {
                "name": service_config.name,
                "status": service_status,
                "enabled": True,
                "url": service_config.url,
                "mode": "魔塔直连" if self.is_modelspace else "本地桥接",
                "stats": self.service_stats[service_key]
            }
        
        return status
    
    def get_status_summary(self) -> str:
        """获取状态摘要"""
        status = self.get_health_status()
        enabled_services = sum(1 for info in status.values() if info["enabled"])
        healthy_services = sum(1 for info in status.values() if info["status"] == "healthy")
        
        mode = "魔塔直连" if self.is_modelspace else "本地桥接"
        
        if enabled_services == 0:
            return f"""
🔍 MCP服务状态监控 ({mode}模式)

**📊 服务概览**: 当前未配置MCP服务

**⚙️ 配置说明**:
- DeepWiki MCP: 需要设置 `DEEPWIKI_MCP_URL` 环境变量
- Fetch MCP: 需要设置 `FETCH_MCP_URL` 环境变量

**🎯 当前模式**: 纯AI生成模式
- 基于行业最佳实践
- 结合项目创意分析
- 生成专业技术方案

总计: 0/2 个服务可用
"""
        
        status_html = f"""
        <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; margin: 15px 0;">
            <h4 style="color: #2d3748; margin-bottom: 10px;">🔍 MCP服务状态监控 ({mode}模式)</h4>
        """
        
        for service_key, info in status.items():
            if info["status"] == "disabled":
                icon = "⚪"
                color = "#6c757d"
                status_text = "未启用"
            elif info["status"] == "healthy":
                icon = "🟢"
                color = "#28a745"
                status_text = f"可用 ({info.get('mode', mode)})"
            else:
                icon = "🔴"
                color = "#dc3545"
                status_text = "连接失败"
            
            # 添加统计信息
            stats = info.get("stats", {})
            stats_text = ""
            if stats.get("total_calls", 0) > 0:
                success_rate = (stats["successful_calls"] / stats["total_calls"]) * 100
                stats_text = f" | 成功率: {success_rate:.1f}% ({stats['total_calls']}次调用)"
            
            status_html += f"""
            <div style="display: flex; align-items: center; margin: 5px 0; font-size: 14px;">
                <span style="margin-right: 8px;">{icon}</span>
                <span style="color: {color}; font-weight: 500;">{info['name']}: {status_text}{stats_text}</span>
            </div>
            """
        
        status_html += f"""
            <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #e2e8f0;">
                <span style="color: #4a5568;">总计: {healthy_services}/{enabled_services} 个服务可用</span>
            </div>
        </div>
        """
        
        return status_html

# 全局MCP服务管理器实例
mcp_manager = MCPServiceManager()