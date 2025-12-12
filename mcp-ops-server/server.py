# server.py
import asyncio
import sys
import os
import json

# MCP 标准导入
import mcp.server.stdio
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.types as types

# ------------------- 设置路径：找到 mock_tools.py -------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_SRC = os.path.abspath(
    os.path.join(CURRENT_DIR, "..", "first_crewai_project", "src", "first_crewai_project")
)
sys.path.append(PROJECT_SRC)
print("已加入 PYTHON 路径:", PROJECT_SRC, file=sys.stderr)

# 导入你已有的工具
from tools.mock_tools import (
    get_nginx_servers,
    get_server_logs_simple,
    get_mysql_logs_simple,
    get_redis_logs_simple,
    get_server_metrics_simple
)

# ------------------- 1. 创建 MCP Server 实例 -------------------
server = Server("mcp-ops-server")


# ------------------- 2. 定义工具列表（适配你的工具） -------------------
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        #工具：获取nginx服务器列表
        types.Tool(
            name="nginx_servers",
            description="获取Nginx服务器列表",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        #工具：获取nginx日志
        types.Tool(
            name="nginx_logs",
            description="获取指定服务器的Nginx日志",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_ip": {
                        "type": "string",
                        "description": "服务器IP地址"
                    },
                    "api_endpoint": {
                        "type": "string",
                        "description": "（可选）自定义API端点"
                    },
                    "keywords": {
                        "type": "string",
                        "description": "（可选）用于过滤日志的关键词"
                    }
                },
                "required": ["server_ip"]  # 只有 server_ip 是必需的
            }
        ),
        types.Tool(
            name="mysql_logs",
            description="获取指定服务器的MySQL慢查询日志",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_ip": {"type": "string", "description": "服务器IP地址"},
                    "keywords": {"type": "string", "description": "（可选）过滤关键词"},
                    "min_duration": {"type": "number", "description": "（可选）最小查询时长（秒）"}
                },
                "required": ["server_ip"]
            }
        ),
        types.Tool(
            name="redis_logs",
            description="获取指定服务器的Redis日志",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_ip": {"type": "string", "description": "服务器IP地址"},
                    "keywords": {"type": "string", "description": "（可选）过滤关键词"},
                    "min_duration": {"type": "number", "description": "（可选）最小命令时长（秒）"}
                },
                "required": ["server_ip"]
            }
        ),
        types.Tool(
            name="server_metrics",
            description="获取服务器的性能指标（CPU、内存、磁盘等）",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_ip": {"type": "string", "description": "服务器IP地址"},
                    "metric_name": {"type": "string", "description": "（可选）指定指标名称，如‘cpu_usage’"}
                },
                "required": ["server_ip"]
            }
        )
    ]


# ------------------- 3. 工具调用处理（调用你的函数） -------------------
@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    try:
        if arguments is None:
            arguments = {}  # 处理无参数的工具（如 nginx_servers）

        # 根据工具名调用对应的函数
        if name == "nginx_servers":
            result = get_nginx_servers.function()

        elif name == "nginx_logs":
            result = get_server_logs_simple.function(
                arguments.get("server_ip"),
                api_endpoint=arguments.get("api_endpoint"),
                keywords=arguments.get("keywords")
            )

        elif name == "mysql_logs":
            result = get_mysql_logs_simple.function(
                arguments.get("server_ip"),
                keywords=arguments.get("keywords"),
                min_duration=arguments.get("min_duration")
            )

        elif name == "redis_logs":
            result = get_redis_logs_simple.function(
                arguments.get("server_ip"),
                keywords=arguments.get("keywords"),
                min_duration=arguments.get("min_duration")
            )

        elif name == "server_metrics":
            result = get_server_metrics_simple.function(
                arguments.get("server_ip"),
                metric_name=arguments.get("metric_name")
            )

        else:
            return [types.TextContent(type="text", text=f"错误：未知的工具 '{name}'")]

        # 将结果格式化为 MCP 标准响应
        formatted_result = json.dumps(result, indent=2, ensure_ascii=False)
        return [types.TextContent(type="text", text=formatted_result)]

    except Exception as e:
        error_msg = f"调用工具 '{name}' 时出错: {str(e)}"
        return [types.TextContent(type="text", text=error_msg)]


# ------------------- 4. 主函数：启动服务器 -------------------
async def main():
    """通过 stdio 运行 MCP 服务器"""
    print("🚀 MCP OPS Server 启动（基于标准 MCP 1.22.0 API）...", file=sys.stderr)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        # 初始化选项，向客户端声明你的服务器能力
        init_options = InitializationOptions(
            server_name="mcp-ops-server",
            server_version="1.0.0",
            capabilities={
                "tools": {},  # 声明支持工具功能
                # 如果你的服务器还提供“资源读取”或“提示词模板”，可在此添加 "resources":{} 或 "prompts":{}
            }
        )
        # 运行服务器主循环
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())