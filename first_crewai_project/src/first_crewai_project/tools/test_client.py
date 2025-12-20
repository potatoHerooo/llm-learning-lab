#!/usr/bin/env python3
"""
测试MCP客户端连接
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_client_tools import (
    get_nginx_servers,
    get_server_metrics
)

print("🧪 测试MCP客户端连接...")

# 测试获取Nginx服务器列表
print("\n1️⃣ 测试: get_nginx_servers()")
result = get_nginx_servers()
print(f"结果: {result[:200]}...")  # 只打印前200个字符

# 测试获取服务器指标
print("\n2️⃣ 测试: get_server_metrics('192.168.1.100')")
result = get_server_metrics('192.168.1.100')
print(f"结果: {result[:200]}...")

print("\n✅ 测试完成")