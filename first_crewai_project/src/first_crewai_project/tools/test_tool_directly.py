
# !/usr/bin/env python3
"""
直接测试工具函数，不通过MCP或CrewAI
"""

import sys
import os

# 添加项目根目录到路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR))
sys.path.append(PROJECT_ROOT)

# 直接导入mock_tools中的原始函数（未经过@tool装饰的版本）
try:
    from mock_tools import (
        get_nginx_servers_raw,
        get_server_logs_simple_raw,
        get_server_metrics_simple_raw,
        get_mysql_logs_simple_raw,
        mysql_runtime_diagnosis_raw,
        get_redis_logs_simple_raw
    )

    print("✅ 成功导入原始工具函数")

    # 测试1: 获取服务器列表
    print("\n🔧 测试1: 获取Nginx服务器列表")
    servers = get_nginx_servers_raw()
    print(f"找到 {len(servers)} 台服务器:")
    for server in servers:
        print(f"  - {server['ip']} ({server['role']})")

    # 测试2: 获取服务器日志
    print("\n🔧 测试2: 获取服务器日志")
    if servers:
        test_ip = servers[0]['ip']
        logs = get_server_logs_simple_raw(test_ip, api_endpoint="/api/v2/data.json")
        print(f"获取到 {len(logs)} 条日志")
        if logs:
            print(f"第一条日志示例: {logs[0]}")

    # 测试3: 获取服务器指标
    print("\n🔧 测试3: 获取服务器指标")
    if servers:
        metrics = get_server_metrics_simple_raw(test_ip, metric_name="cpu")
        print(f"获取到指标: {metrics}")

    # 测试4: 获取MySQL日志
    print("\n🔧 测试4: 获取MySQL日志")
    if servers:
        mysql_logs, next_time = get_mysql_logs_simple_raw(test_ip, keywords="error")
        print(f"获取到 {len(mysql_logs)} 条MySQL日志")
        if mysql_logs:
            print(f"第一条MySQL日志示例: {mysql_logs[0]}")

    # 测试5: MySQL运行时诊断
    print("\n🔧 测试5: MySQL运行时诊断")
    diagnosis = mysql_runtime_diagnosis_raw(test_ip, "processlist")
    print(f"MySQL进程列表: {diagnosis}")

    # 测试6: 获取Redis日志
    print("\n🔧 测试6: 获取Redis日志")
    redis_logs = get_redis_logs_simple_raw(test_ip, keywords="error")
    print(f"获取到 {len(redis_logs)} 条Redis日志")
    if redis_logs:
        print(f"第一条Redis日志示例: {redis_logs[0]}")

    print("\n✅ 所有工具测试完成!")

except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback

    traceback.print_exc()
