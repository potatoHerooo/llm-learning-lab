import asyncio
import json
import random
import sys
from datetime import datetime
from typing import Any, Dict
import mcp.server.stdio
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.types as types

# 创建 MCP 服务器实例
server = Server("mock-monitor-server")


# 模拟监控数据
def generate_mock_metrics(server_ip: str) -> Dict[str, Any]:
    """生成模拟监控指标"""
    return {
        "server_ip": server_ip,
        "timestamp": datetime.now().isoformat(),
        "cpu_usage": random.randint(5, 95),  # CPU使用率 5%-95%
        "memory_usage": random.randint(30, 90),  # 内存使用率 30%-90%
        "disk_usage": random.randint(20, 85),  # 磁盘使用率 20%-85%
        "load_average": [random.uniform(0.1, 3.0) for _ in range(3)],  # 1,5,15分钟负载
        "network_rx_mb": random.randint(10, 1000),  # 接收流量 MB
        "network_tx_mb": random.randint(10, 1000),  # 发送流量 MB
    }


# 工具列表
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_cpu_usage",
            description="获取指定服务器的CPU使用率",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_ip": {
                        "type": "string",
                        "description": "服务器IP地址，例如：192.168.1.100"
                    }
                },
                "required": ["server_ip"]
            }
        ),
        types.Tool(
            name="get_memory_usage",
            description="获取指定服务器的内存使用率",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_ip": {
                        "type": "string",
                        "description": "服务器IP地址"
                    }
                },
                "required": ["server_ip"]
            }
        ),
        types.Tool(
            name="get_disk_usage",
            description="获取指定服务器的磁盘使用率",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_ip": {
                        "type": "string",
                        "description": "服务器IP地址"
                    }
                },
                "required": ["server_ip"]
            }
        ),
        types.Tool(
            name="get_all_metrics",
            description="获取指定服务器的所有监控指标",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_ip": {
                        "type": "string",
                        "description": "服务器IP地址"
                    }
                },
                "required": ["server_ip"]
            }
        )
    ]


# 工具调用处理
@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any] | None) -> list[types.TextContent]:
    try:
        if arguments is None:
            raise ValueError("参数不能为空")

        server_ip = arguments.get("server_ip", "unknown")
        metrics = generate_mock_metrics(server_ip)

        if name == "get_cpu_usage":
            return [types.TextContent(
                type="text",
                text=f"服务器 {server_ip} 的 CPU 使用率：{metrics['cpu_usage']}%"
            )]

        elif name == "get_memory_usage":
            return [types.TextContent(
                type="text",
                text=f"服务器 {server_ip} 的内存使用率：{metrics['memory_usage']}%"
            )]

        elif name == "get_disk_usage":
            return [types.TextContent(
                type="text",
                text=f"服务器 {server_ip} 的磁盘使用率：{metrics['disk_usage']}%"
            )]

        elif name == "get_all_metrics":
            formatted_metrics = json.dumps(metrics, indent=2, ensure_ascii=False)
            return [types.TextContent(
                type="text",
                text=f"服务器 {server_ip} 的完整监控指标：\n{formatted_metrics}"
            )]

        else:
            raise ValueError(f"未知工具: {name}")

    except Exception as e:
        error_msg = f"调用工具 {name} 时出错: {str(e)}"
        return [types.TextContent(type="text", text=error_msg)]


async def main():
    """主函数，通过 stdio 运行服务器"""
    print("启动监控中心 MCP 服务器...", file=sys.stderr)
    print("注意：请不要向 stdout 输出任何内容，以免干扰 MCP 协议通信", file=sys.stderr)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        # 创建初始化选项，指定服务器的能力
        init_options = InitializationOptions(
            server_name="mock-monitor-server",
            server_version="1.0.0",
            capabilities={
                "tools": {},  # 声明支持工具
                "resources": {},  # 声明支持资源（可选）
                "prompts": {},  # 声明支持提示（可选）
            }
        )

        await server.run(
            read_stream,
            write_stream,
            init_options
        )


if __name__ == "__main__":
    # 确保所有日志输出到 stderr
    sys.stderr.write("监控中心 MCP 服务器启动...\n")
    asyncio.run(main())