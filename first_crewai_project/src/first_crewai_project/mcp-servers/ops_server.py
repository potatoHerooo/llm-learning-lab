#!/usr/bin/env python3
import sys
import os
from mcp.server.fastmcp import FastMCP

# ================== 路径修正 ==================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
sys.path.append(PROJECT_ROOT)

print("✅ OPS MCP PYTHON PATH:", PROJECT_ROOT, file=sys.stderr)

# ================== 导入运维类工具 ==================
# ✅ 正确写法
from tools.mock_tools import (
    get_nginx_servers,
    get_server_logs_simple,
    get_mysql_logs_simple,
    mysql_runtime_diagnosis,
    get_redis_logs_simple,
)


# ================== 创建 FastMCP Server ==================
server = FastMCP(
    name="ops-center",
    instructions=(
        "运维中心 MCP Server，"
        "提供 Nginx / MySQL / Redis 的日志分析、慢请求、错误事件与运行时诊断能力。"
    )
)

# ================== 注册运维工具 ==================
server.tool(get_nginx_servers)
server.tool(get_server_logs_simple)
server.tool(get_mysql_logs_simple)
server.tool(mysql_runtime_diagnosis)
server.tool(get_redis_logs_simple)

# ================== 启动 Server ==================
if __name__ == "__main__":
    print("🚀 OPS Center MCP 启动（FastMCP, streamable-http）", file=sys.stderr)
    server.run(
        transport="streamable-http"
    )

