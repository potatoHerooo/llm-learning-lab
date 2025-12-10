#!/usr/bin/env python3
import asyncio
from mcp.server import Server
import mcp.server.stdio
from datetime import datetime

# 创建MCP服务器实例
server = Server("test-server")


@server.list_tools()
async def handle_list_tools():
    """告诉客户端我们有哪些工具"""
    return [
        {
            "name": "get_current_time",
            "description": "获取当前时间",
            "inputSchema": {
                "type": "object",
                "properties": {}  # 这个工具不需要参数
            }
        }
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """处理工具调用请求"""
    if name == "get_current_time":
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"当前时间: {current_time}"
                }
            ]
        }
    else:
        raise ValueError(f"未知工具: {name}")


async def main():
    """启动服务器"""
    print("🚀 启动MCP测试服务器...")
    print("等待客户端连接...")

    # 使用标准输入输出作为通讯通道
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            mcp.server.NotificationOptions()
        )


if __name__ == "__main__":
    asyncio.run(main())