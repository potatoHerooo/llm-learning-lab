#!/usr/bin/env python3
"""
模拟工具模块 - 为故障诊断智能体提供模拟数据
"""
from crewai.tools import tool
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

# 排除test_data从文件层面导入失败：修改为绝对导入，去掉相对导入的点
try:
    # 尝试从当前目录导入
    from test_data import (
        generate_servers,
        generate_nginx_logs_for_server,
        generate_metrics_for_server
    )
except ImportError:
    # 如果失败，尝试从父目录导入
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from test_data import (
        generate_servers,
        generate_nginx_logs_for_server,
        generate_metrics_for_server
    )

# ==================== 简化的工具版本（解决CrewAI验证问题）====================

@tool("获取Nginx服务器列表")
def get_nginx_servers() -> List[Dict[str, Any]]:
    """获取所有Nginx服务器的IP地址和基本信息。"""
    print(f"[工具调用] get_nginx_servers() - 获取服务器列表")
    servers = generate_servers()
    print(f"  找到 {len(servers)} 台服务器:")
    for server in servers:
        print(f"  - {server['ip']} ({server['role']}, 区域: {server['region']})")
    return servers


@tool("获取服务器日志")
def get_server_logs_simple(
        server_ip: str,
        api_endpoint: str = None,
        keywords: Union[str, List[str]] = None
) -> List[Dict[str, Any]]:
    """获取服务器日志，支持按接口路径过滤和关键词过滤（增强版）
    参数：
        server_ip ：服务器IP地址
        api_endpoint：重点关注的文件
        keywords：日志关键词
    """
    print(f"[工具调用] get_server_logs_simple('{server_ip}', api_endpoint={api_endpoint}, keywords={keywords})")

    # 生成日志
    logs = generate_nginx_logs_for_server(server_ip, 60)

    # ------------------------------
    # ① 按 接口路径 过滤
    # ------------------------------
    if api_endpoint:
        logs = [log for log in logs if api_endpoint in log]

    # ------------------------------
    # ② 按关键词过滤：不区分大小写，可以用自然语言告诉工具
    # ------------------------------
    if keywords:
        if isinstance(keywords, str):
            keywords = [keywords]  # 统一处理成列表

        filtered = []
        for log in logs:
            if any(k.lower() in log.lower() for k in keywords):
                filtered.append(log)

        logs = filtered

    print(f"[工具调用] 找到 {len(logs)} 条相关日志")

    # ------------------------------
    # ③ 解析结构化日志：大模型偏向使用的JSON格式的数据
    # ------------------------------
    structured_logs = []

    for log in logs[:10]:  # 只处理前10条
        try:
            import re

            # 路径
            path_match = re.search(r'"GET\s+([^\s?]+)', log) or \
                         re.search(r'"POST\s+([^\s?]+)', log)
            path = path_match.group(1) if path_match else "unknown"

            # 状态码
            status_match = re.search(r'"\s+(\d{3})\s+', log)
            status_code = status_match.group(1) if status_match else "000"

            # 响应时间
            rt_match = re.search(r'rt=([\d.]+)', log) or \
                       re.search(r'([\d.]+)$', log)
            response_time = float(rt_match.group(1)) if rt_match else 0.0

            # IP
            ip_match = re.match(r'(\S+)', log)
            client_ip = ip_match.group(1) if ip_match else "0.0.0.0"

            # 时间戳
            time_match = re.search(r'\[(.*?)\]', log)
            timestamp = time_match.group(1) if time_match else ""

            structured_logs.append({
                'timestamp': timestamp,
                'client_ip': client_ip,
                'method': 'GET' if 'GET' in log else 'POST',
                'path': path,
                'status_code': status_code,
                'response_time': response_time,
                'raw_log': log[:100] + "..." if len(log) > 100 else log
            })

        except Exception as e:
            print(f"[警告] 解析日志失败: {e}")
            continue

    return structured_logs


@tool("获取服务器指标")
def get_server_metrics_simple(
        server_ip: str,
        metric_name: str = None
) -> Dict[str, Any]:
    """
    简化的指标获取工具，避免复杂的参数验证问题。

    参数:
        server_ip (str): 服务器IP地址
        metric_name (str): 指标名称（可选）

    返回:
        指标数据
    """
    print(f"[工具调用] get_server_metrics_simple('{server_ip}', metric_name={metric_name})")

    # 生成模拟指标
    all_metrics = generate_metrics_for_server(server_ip, 60)

    # 过滤指定的指标
    if metric_name:
        metric_mapping = {
            "cpu": "cpu_percent",
            "cpu_usage_total": "cpu_percent",
            "内存": "memory_percent",
            "memory": "memory_percent",
            "磁盘": "disk_percent",
            "disk": "disk_percent",
            "成功率": "success_rate",
            "错误率": "success_rate",
            "延迟": "avg_latency_ms",
            "响应时间": "avg_latency_ms"
        }

        actual_key = metric_mapping.get(metric_name.lower(), metric_name)
        if actual_key in all_metrics:
            return {actual_key: all_metrics[actual_key]}
        else:
            return {"error": f"未找到指标: {metric_name}"}
    else:
        # 返回所有指标
        return all_metrics


# ==================== 原来的完整版本（仅供内部使用） ====================

def get_server_logs_full(
        server_ip: str,
        keywords: Optional[Union[str, List[str]]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        time_range_minutes: int = 60,
        max_logs: int = 10000,
        error_codes: Optional[List[str]] = None,
        min_response_time: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    完整的日志获取函数（但不用作CrewAI工具）
    """
    # ... 完整实现（但不用@tool装饰器）...
    pass


def get_server_metrics_full(
        server_ip: str,
        time_range_minutes: int = 60,
        metric_name: Optional[Union[str, List[str]]] = None
) -> Dict[str, Any]:
    """
    完整的指标获取函数（但不用作CrewAI工具）
    """
    # ... 完整实现（但不用@tool装饰器）...
    pass


# 在 mock_tools.py 文件的最后添加：

def test_tools_locally():
    """本地测试工具函数"""
    print("🔧 本地测试工具函数")

    # 测试服务器列表
    servers = get_nginx_servers.function()
    print(f"获取到 {len(servers)} 台服务器")

    # 测试获取特定服务器的日志
    test_server = "10.0.2.101"
    print(f"\n测试服务器 {test_server} 的日志:")
    logs = get_server_logs_simple.function(test_server, api_endpoint="/api/v2/data.json")
    print(f"获取到 {len(logs)} 条日志")

    if logs:
        for log in logs[:3]:
            print(f"  - 状态码: {log['status_code']}, 路径: {log['path']}")

    # 测试获取指标
    print(f"\n测试服务器 {test_server} 的指标:")
    metrics = get_server_metrics_simple.function(test_server, metric_name="cpu")
    print(f"CPU使用率: {metrics.get('cpu_percent', 'N/A')}%")

    print("\n✅ 本地测试完成")


def verify_log_format():
    """验证日志格式是否正确"""
    print("🔍 验证日志格式")
    print("=" * 60)

    from test_data import generate_nginx_logs_for_server

    # 生成测试日志
    test_logs = generate_nginx_logs_for_server("10.0.2.101", 1)  # 生成少量日志

    if not test_logs:
        print("❌ 没有生成日志！")
        return

    print(f"生成 {len(test_logs)} 条日志")
    print("\n第一条日志:")
    print(f"  {test_logs[0]}")

    # 手动解析
    log = test_logs[0]
    parts = log.split()

    print(f"\n分割后得到 {len(parts)} 部分:")
    for i, part in enumerate(parts):
        print(f"  [{i}] {part}")

    print("\n尝试解析:")
    try:
        # 方法1：按空格分割
        ip = parts[0]
        timestamp = parts[3] + " " + parts[4]  # [01/Jan/2024:12:00:00 +0000]
        request = parts[5] + " " + parts[6] + " " + parts[7]  # "GET /api/v2/data.json HTTP/1.1"
        status_code = parts[8]
        response_size = parts[9]

        print(f"  IP: {ip}")
        print(f"  时间: {timestamp}")
        print(f"  请求: {request}")
        print(f"  状态码: {status_code}")
        print(f"  响应大小: {response_size}")

        # 剩下的部分
        for i in range(10, len(parts)):
            print(f"  [{i}] {parts[i]}")

    except Exception as e:
        print(f"❌ 解析失败: {e}")


# 在文件末尾添加
if __name__ == "__main__":
    verify_log_format()