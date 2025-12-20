#!/usr/bin/env python3
"""
运维MCP服务器 - 简化版，直接提供HTTP接口
"""

import sys
import os
import logging
from fastapi import FastAPI, HTTPException,Request
import uvicorn
import json

# ================== 设置详细日志 ==================
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)

# ================== 路径修正 ==================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
TOOLS_DIR = os.path.join(PROJECT_ROOT, "tools")
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, TOOLS_DIR)

print("✅ OPS MCP 简化版本启动", file=sys.stderr)

# ================== 导入运维工具 ==================
try:
    from mock_tools import (
        get_nginx_servers_raw as get_nginx_servers_func,
        get_server_logs_simple_raw as get_server_logs_simple_func,
        get_mysql_logs_simple_raw as get_mysql_logs_simple_func,
        mysql_runtime_diagnosis_raw as mysql_runtime_diagnosis_func,
        get_redis_logs_simple_raw as get_redis_logs_simple_func,
    )

    print("✅ 成功导入运维工具", file=sys.stderr)
except ImportError as e:
    print(f"❌ 导入运维工具失败: {e}", file=sys.stderr)
    sys.exit(1)

# ================== 创建FastAPI应用 ==================
app = FastAPI(title="运维MCP服务器", version="1.0.0")


# ================== 定义工具端点 ==================

@app.get("/")
async def root():
    """根端点"""
    return {
        "name": "运维MCP服务器",
        "version": "1.0.0",
        "tools": [
            "get_nginx_servers",
            "get_server_logs_simple",
            "get_mysql_logs_simple",
            "mysql_runtime_diagnosis",
            "get_redis_logs_simple"
        ]
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.post("/tools/call")
async def call_tool(request: Request):
    """调用工具"""
    try:
        # 从请求中获取数据
        data = await request.json()
        tool_name = data.get("tool_name")
        arguments = data.get("arguments", {})

        print(f"[DEBUG] 调用工具: {tool_name}, 参数: {arguments}", file=sys.stderr)

        if tool_name == "get_nginx_servers":
            result = get_nginx_servers_func()
        elif tool_name == "get_server_logs_simple":
            result = get_server_logs_simple_func(
                arguments.get("server_ip"),
                arguments.get("api_endpoint"),
                arguments.get("keywords")
            )
        elif tool_name == "get_mysql_logs_simple":
            logs, _ = get_mysql_logs_simple_func(
                server_ip=arguments.get("server_ip"),
                keywords=arguments.get("keywords", ""),
                min_duration_s=arguments.get("min_duration_s", 0.0)
            )
            result = logs
        elif tool_name == "mysql_runtime_diagnosis":
            result = mysql_runtime_diagnosis_func(
                arguments.get("server_ip"),
                arguments.get("action")
            )
        elif tool_name == "get_redis_logs_simple":
            result = get_redis_logs_simple_func(
                arguments.get("server_ip"),
                arguments.get("keywords"),
                arguments.get("min_duration")
            )
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
                "name": "get_server_logs_simple",
                "description": "获取指定服务器的Nginx日志。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "server_ip": {"type": "string"},
                        "api_endpoint": {"type": "string"},
                        "keywords": {"type": "string"}
                    }
                }
            },
            {
                "name": "get_mysql_logs_simple",
                "description": "获取MySQL日志。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "server_ip": {"type": "string"},
                        "keywords": {"type": "string"},
                        "min_duration_s": {"type": "number"}
                    }
                }
            },
            {
                "name": "mysql_runtime_diagnosis",
                "description": "MySQL运行时诊断。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "server_ip": {"type": "string"},
                        "action": {"type": "string"}
                    }
                }
            },
            {
                "name": "get_redis_logs_simple",
                "description": "获取Redis日志。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "server_ip": {"type": "string"},
                        "keywords": {"type": "string"},
                        "min_duration": {"type": "number"}
                    }
                }
            }
        ]
    }


if __name__ == "__main__":
    print("🚀 Ops MCP 服务器启动（端口: 3000）", file=sys.stderr)
    uvicorn.run(app, host="0.0.0.0", port=3000)