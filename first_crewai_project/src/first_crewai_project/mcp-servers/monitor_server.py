# 同样修改导入部分：
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
# 向上到父目录（first_crewai_project）
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
sys.path.append(PROJECT_ROOT)
print("已加入 PYTHON 路径:", PROJECT_ROOT, file=sys.stderr)

# 导入监控工具
from ..tools.mock_tools import get_server_metrics_simple

# ------------------- 1. 创建 MCP Server 实例 -------------------
server = Server("mcp-monitor-server")  # ⚠️ 注意这里要改名字！

# ------------------- 2. 定义工具列表（适配你的工具） -------------------
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
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
        if name == "server_metrics":
            result = get_server_metrics_simple.run(
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
            server_name="mcp-monitor-server",
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