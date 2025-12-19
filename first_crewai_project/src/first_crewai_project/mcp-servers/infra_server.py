#!/usr/bin/env python3
import sys
import os
from mcp.server.fastmcp import FastMCP

# ================== 路径修正 ==================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
sys.path.append(PROJECT_ROOT)

print("✅ INFRA MCP PYTHON PATH:", PROJECT_ROOT, file=sys.stderr)

# ================== 导入所有工具 ==================
# 注意：这里导入mock_tools中的原始函数（不是@tool装饰的版本）
# MCP服务器需要的是原始函数，而不是@tool装饰后的Tool对象
from mock_tools import (
    get_nginx_servers_raw as get_nginx_servers_func,
    get_server_logs_simple_raw as get_server_logs_simple_func,
    get_mysql_logs_simple_raw as get_mysql_logs_simple_func,
    mysql_runtime_diagnosis_raw as mysql_runtime_diagnosis_func,
    get_redis_logs_simple_raw as get_redis_logs_simple_func,
    get_server_metrics_simple_raw as get_server_metrics_simple_func,
)

# ================== 创建 FastMCP Server ==================
server = FastMCP(
    name="infra-center",
    instructions=(
        "基础设施 MCP Server，统一提供：\n"
        "- 运维能力：Nginx / MySQL / Redis 日志、慢请求、错误与运行时诊断\n"
        "- 监控能力：CPU、内存、磁盘、成功率、延迟等服务器与接口指标\n\n"
        "用于上层 Agent 进行故障诊断与根因分析。"
    )
)

# ================== 注册所有工具 ==================
# 注册为MCP工具
@server.tool()
def get_nginx_servers():
    """获取所有Nginx服务器的IP地址和基本信息。"""
    return get_nginx_servers_func()

@server.tool()
def get_server_logs_simple(server_ip: str, api_endpoint: str = None, keywords=None):
    """获取指定服务器的Nginx日志。"""
    return get_server_logs_simple_func(server_ip, api_endpoint, keywords)

@server.tool()
def get_mysql_logs_simple(server_ip: str, keywords: str = "", min_duration_s: float = 0.0):
    """获取MySQL日志。"""
    logs, _ = get_mysql_logs_simple_func(
        server_ip=server_ip,
        keywords=keywords,
        min_duration_s=min_duration_s
    )
    return logs

@server.tool()
def mysql_runtime_diagnosis(server_ip: str, action: str):
    """MySQL运行时诊断。"""
    return mysql_runtime_diagnosis_func(server_ip, action)

@server.tool()
def get_redis_logs_simple(server_ip: str, keywords=None, min_duration=None):
    """获取Redis日志。"""
    return get_redis_logs_simple_func(server_ip, keywords, min_duration)

@server.tool()
def get_server_metrics_simple(server_ip: str, metric_name: str = None):
    """获取服务器性能指标。"""
    return get_server_metrics_simple_func(server_ip, metric_name)

# ================== 启动 Server ==================
if __name__ == "__main__":
    print("🚀 Infra Center MCP 启动（FastMCP, streamable-http）", file=sys.stderr)
    server.run(transport="streamable-http")
