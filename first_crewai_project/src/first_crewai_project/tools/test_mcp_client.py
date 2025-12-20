"""
测试MCP客户端连接
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp_client_tools import ops_client, monitor_client


async def test_connections():
    print("🧪 测试MCP客户端连接...")

    # 测试运维服务器
    print("\n1. 测试运维服务器工具:")
    result = await ops_client.call_tool("get_nginx_servers")
    print(f"   ✅ get_nginx_servers: {result[:100]}...")

    # 测试监控服务器
    print("\n2. 测试监控服务器工具:")
    result = await monitor_client.call_tool("get_server_metrics_simple",
                                            {"server_ip": "192.168.1.100"})
    print(f"   ✅ get_server_metrics_simple: {result[:100]}...")

    print("\n🎉 测试完成！所有连接正常")


if __name__ == "__main__":
    asyncio.run(test_connections())