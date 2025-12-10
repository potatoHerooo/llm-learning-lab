#!/usr/bin/env python3
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client import stdio


async def main():
    """MCP客户端示例"""
    # 配置服务器参数（通过命令行启动服务器）
    server_params = StdioServerParameters(
        command="python",  # 执行命令
        args=["mcp_test_server.py"]  # 参数：服务器脚本
    )

    print("🔌 连接到MCP服务器...")

    async with ClientSession(*await stdio.connect_to_server(server_params)) as session:
        # 步骤1: 初始化握手
        print("🤝 正在进行初始化握手...")
        await session.initialize()

        # 步骤2: 列出可用工具
        print("📋 获取可用工具列表...")
        tools = await session.list_tools()
        print(f"找到 {len(tools)} 个工具:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")

        # 步骤3: 调用工具
        print("🛠️ 调用 get_current_time 工具...")
        result = await session.call_tool("get_current_time", {})

        # 步骤4: 处理结果
        for content in result.content:
            if content.type == "text":
                print(f"📄 服务器返回: {content.text}")

        print("✅ 测试完成！")


if __name__ == "__main__":
    asyncio.run(main())