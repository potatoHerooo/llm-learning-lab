#!/usr/bin/env python3
import sys
import os
from mcp.server.fastmcp import FastMCP

# ================== 路径修正 ==================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
sys.path.append(PROJECT_ROOT)

print("✅ MONITOR MCP PYTHON PATH:", PROJECT_ROOT, file=sys.stderr)

# ================== 导入监控类工具 ==================
# ✅ 正确
from tools.mock_tools import get_server_metrics_simple

# ================== 创建 FastMCP Server ==================
server = FastMCP(
    name="monitor-center",
    instructions=(
        "监控中心 MCP Server，"
        "提供服务器与接口的 CPU、内存、磁盘、成功率、延迟等性能指标。"
    )
)

# ================== 注册监控工具 ==================
server.tool(get_server_metrics_simple)

# ================== 启动 Server ==================
if __name__ == "__main__":
    print("📊 Monitor Center MCP 启动（FastMCP, streamable-http）", file=sys.stderr)
    server.run(
        transport="streamable-http"
    )

