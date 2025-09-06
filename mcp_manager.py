"""
MCP服务管理器
统一管理多个MCP服务的调用、监控和路由
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

from config import config, MCPServiceConfig

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

class MCPServiceManager:
    """MCP服务管理器"""
    
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
    
    def get_service_for_url(self, url: str) -> List[MCPServiceType]:
        """根据URL智能选择MCP服务 - 优化大众化场景"""
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
                "investment", "fitness", "diet", "blockchain", "web3"
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
        payload: Dict[str, Any]
    ) -> MCPCallResult:
        """调用单个MCP服务"""
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
        
        try:
            logger.info(f"🔥 调用 {service_config.name} - URL: {service_config.url}")
            logger.info(f"🔥 载荷: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            
            headers = {"Content-Type": "application/json"}
            if service_config.api_key:
                headers["Authorization"] = f"Bearer {service_config.api_key}"
            
            response = requests.post(
                service_config.url,
                headers=headers,
                json=payload,
                timeout=service_config.timeout
            )
            
            execution_time = time.time() - start_time
            
            logger.info(f"🔥 响应状态: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # 尝试多种响应格式
                content = self._extract_content_from_response(data)
                
                if content and len(str(content).strip()) > 10:
                    result = MCPCallResult(
                        success=True,
                        data=str(content),
                        service_name=service_config.name,
                        execution_time=execution_time
                    )
                    self._update_service_stats(service_type, True, execution_time)
                    return result
                else:
                    error_msg = f"返回数据为空或格式错误: {data}"
                    logger.warning(f"⚠️ {service_config.name} {error_msg}")
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
                logger.error(f"❌ {service_config.name} 调用失败: {error_msg}")
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
            error_msg = f"调用超时 ({service_config.timeout}s)"
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
    
    def _extract_content_from_response(self, data: Dict) -> Optional[str]:
        """从响应中提取内容"""
        # 尝试多种可能的响应格式
        content_keys = ["data", "result", "content", "message", "text"]
        
        for key in content_keys:
            if key in data and data[key]:
                return str(data[key])
        
        # 如果没有找到标准字段，返回整个数据的字符串表示
        return str(data) if data else None
    
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
        """从URL获取知识 - 支持多MCP服务协作"""
        if not url or not url.strip():
            return False, ""
        
        url = url.strip()
        
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
        
        # 并行调用多个MCP服务
        for service_type in suitable_services:
            payload = self._build_payload_for_service(service_type, url)
            result = self.call_single_mcp_service(service_type, payload)
            
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
    
    def _build_payload_for_service(self, service_type: MCPServiceType, url: str) -> Dict[str, Any]:
        """为不同的MCP服务构建载荷"""
        if service_type == MCPServiceType.DEEPWIKI:
            return {
                "action": "deepwiki_fetch",
                "params": {
                    "url": url,
                    "mode": "aggregate"
                }
            }
        elif service_type == MCPServiceType.FETCH:
            return {
                "action": "fetch",
                "params": {
                    "url": url
                }
            }
        else:
            return {"url": url}
    
    def _combine_knowledge_sources(self, url: str, sources: List[Dict]) -> str:
        """整合多个知识源"""
        if not sources:
            return ""
        
        if len(sources) == 1:
            source = sources[0]
            return f"📖 **{source['service']}**：\n\n{source['content']}"
        
        # 多源整合
        fusion_header = f"""
## 🧠 多源知识融合 ({len(sources)}个知识源)

**🔗 原始链接：** {url}

**🎯 MCP服务协作：** 智能路由系统已为您整合以下知识源

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
            
            try:
                # 简单的健康检查
                health_url = f"{service_config.url.rstrip('/')}{service_config.health_check_path}"
                response = requests.get(health_url, timeout=5)
                
                status[service_key] = {
                    "name": service_config.name,
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "enabled": True,
                    "url": service_config.url,
                    "response_time": response.elapsed.total_seconds(),
                    "stats": self.service_stats[service_key]
                }
            except Exception as e:
                status[service_key] = {
                    "name": service_config.name,
                    "status": "error",
                    "enabled": True,
                    "url": service_config.url,
                    "error": str(e),
                    "stats": self.service_stats[service_key]
                }
        
        return status
    
    def get_status_summary(self) -> str:
        """获取状态摘要HTML"""
        status = self.get_health_status()
        enabled_services = sum(1 for info in status.values() if info["enabled"])
        healthy_services = sum(1 for info in status.values() if info["status"] == "healthy")
        
        if enabled_services == 0:
            return """
🔍 MCP服务状态监控

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
        
        status_html = """
        <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; margin: 15px 0;">
            <h4 style="color: #2d3748; margin-bottom: 10px;">🔍 MCP服务状态监控</h4>
        """
        
        for service_key, info in status.items():
            if info["status"] == "disabled":
                icon = "⚪"
                color = "#6c757d"
                status_text = "未启用"
            elif info["status"] == "healthy":
                icon = "🟢"
                color = "#28a745"
                status_text = f"可用 ({info.get('response_time', 0):.2f}s)"
            elif info["status"] == "unhealthy":
                icon = "🟡"
                color = "#ffc107"
                status_text = "响应异常"
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
    
    def get_debug_status(self) -> str:
        """获取详细的调试状态信息"""
        debug_lines = [
            "## 🔧 MCP服务详细诊断",
            "",
            "### 📋 环境变量检查:",
        ]
        
        env_vars = {
            "DEEPWIKI_SSE_URL": os.getenv("DEEPWIKI_SSE_URL"),
            "FETCH_SSE_URL": os.getenv("FETCH_SSE_URL")
        }
        
        for var_name, var_value in env_vars.items():
            if var_value:
                debug_lines.append(f"- **{var_name}**: ✅ 已设置 ({var_value[:50]}...)")
            else:
                debug_lines.append(f"- **{var_name}**: ❌ 未设置")
        
        debug_lines.extend([
            "",
            "### 🔍 服务配置状态:"
        ])
        
        for service_key, service_config in self.services.items():
            stats = self.service_stats[service_key]
            debug_lines.append(f"")
            debug_lines.append(f"**{service_config.name}** ({service_key}):")
            debug_lines.append(f"- URL: {service_config.url or '未配置'}")
            debug_lines.append(f"- 启用状态: {'✅' if service_config.enabled else '❌'}")
            debug_lines.append(f"- 超时设置: {service_config.timeout}秒")
            debug_lines.append(f"- 总调用次数: {stats['total_calls']}")
            debug_lines.append(f"- 成功次数: {stats['successful_calls']}")
            debug_lines.append(f"- 失败次数: {stats['failed_calls']}")
            if stats['average_response_time'] > 0:
                debug_lines.append(f"- 平均响应时间: {stats['average_response_time']:.2f}秒")
        
        debug_lines.extend([
            "",
            "### 📊 调用历史 (最近5次):"
        ])
        
        recent_calls = self.call_history[-5:] if self.call_history else []
        if recent_calls:
            for i, call in enumerate(recent_calls, 1):
                status_emoji = "✅" if call.success else "❌"
                debug_lines.append(f"{i}. {status_emoji} {call.service_name} - {call.execution_time:.2f}s")
                if call.error_message:
                    debug_lines.append(f"   错误: {call.error_message}")
        else:
            debug_lines.append("暂无调用历史")
        
        return "\n".join(debug_lines)

# 全局MCP服务管理器实例
mcp_manager = MCPServiceManager()