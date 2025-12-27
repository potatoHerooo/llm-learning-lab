#!/usr/bin/env python3
"""
监控MCP服务器 - 简化版，直接提供HTTP接口
端口: 3001
"""

import sys
import os
from fastapi import FastAPI, HTTPException
import uvicorn

# ================== 路径修正 ==================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
TOOLS_DIR = os.path.join(PROJECT_ROOT, "tools")
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, TOOLS_DIR)

print("✅ MONITOR MCP 简化版本启动", file=sys.stderr)

# ================== 导入监控工具 ==================
try:
    from mock_tools import (
        get_nginx_servers_raw as get_nginx_servers_func,
        get_server_metrics_simple_raw as get_server_metrics_simple_func,
    )

    print("✅ 成功导入监控工具", file=sys.stderr)
except ImportError as e:
    print(f"❌ 导入监控工具失败: {e}", file=sys.stderr)
    sys.exit(1)

# ================== 创建FastAPI应用 ==================
app = FastAPI(title="监控MCP服务器", version="1.0.0")


# ================== 定义工具端点 ==================

@app.get("/")
async def root():
    """根端点"""
    return {
        "name": "监控MCP服务器",
        "version": "1.0.0",
        "tools": [
            "get_nginx_servers",
            "get_server_metrics_simple"
        ]
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


from pydantic import BaseModel


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict = {}


# ... 其他代码保持不变 ...

@app.post("/tools/call")
async def call_tool(request: ToolCallRequest):
    """调用工具"""
    try:
        tool_name = request.tool_name
        arguments = request.arguments

        print(f"[DEBUG] 调用工具: {tool_name}, 参数: {arguments}", file=sys.stderr)

        if tool_name == "get_nginx_servers":
            result = get_nginx_servers_func()
        elif tool_name == "get_server_metrics_simple":
            # 直接传递参数
            server_ip = arguments.get("server_ip")
            metric_name = arguments.get("metric_name")

            print(f"[DEBUG] 调用指标工具: server_ip={server_ip}, metric_name={metric_name}", file=sys.stderr)

            result = get_server_metrics_simple_func(server_ip, metric_name)
        else:
            raise HTTPException(status_code=404, detail=f"工具 '{tool_name}' 不存在")

        return {"result": result}

    except Exception as e:
        print(f"[ERROR] 工具调用失败: {e}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/list")
async def list_tools():
    """列出所有可用工具"""
    return {
        "tools": [
            {
                "name": "get_nginx_servers",
                "description": "获取所有Nginx服务器的IP地址和基本信息。",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_server_metrics_simple",
                "description": "获取服务器性能指标。支持单个指标、多个指标或全部指标。常见指标别名：cpu_usage->cpu_percent, memory_usage->memory_percent, request_success_rate->success_rate, avg_latency->avg_latency_ms",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "server_ip": {"type": "string"},
                        "metric_name": {
                            "type": ["string", "array", "null"],
                            "description": "指标名称。可以是：字符串（单个指标），数组（多个指标），null（所有指标）。"
                        }
                    }
                }
            }
        ]
    }

if __name__ == "__main__":
    print("🚀 Monitor MCP 服务器启动（端口: 3001）", file=sys.stderr)
    uvicorn.run(app, host="0.0.0.0", port=3001)