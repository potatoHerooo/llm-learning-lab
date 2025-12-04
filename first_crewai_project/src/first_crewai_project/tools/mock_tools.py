#!/usr/bin/env python3
"""
模拟工具模块 - 为故障诊断智能体提供模拟数据
"""
from crewai.tools import BaseTool, tool
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from .test_data import (
    generate_servers,
    generate_nginx_logs_for_server,
    generate_metrics_for_server
)


@tool("获取Nginx服务器列表")
def get_nginx_servers() -> List[Dict[str, Any]]:
    """
    获取所有Nginx服务器的IP地址和基本信息。

    返回:
        List[Dict]: 服务器列表，每个服务器包含IP、主机名、角色、区域和状态
    """
    print(f"[工具调用] get_nginx_servers() - 获取服务器列表")
    servers = generate_servers()

    print(f"  找到 {len(servers)} 台服务器:")
    for server in servers:
        print(f"  - {server['ip']} ({server['role']}, 区域: {server['region']})")

    return servers


@tool("根据服务器IP获取Nginx日志")
def get_server_logs(server_ip: str, time_range_minutes: int = 60) -> List[str]:
    """
    从指定服务器获取最近一段时间内的Nginx访问日志。

    参数:
        server_ip (str): 服务器IP地址
        time_range_minutes (int): 时间范围（分钟），默认60分钟

    返回:
        List[str]: Nginx access_log 日志行列表
    """
    print(f"\n[工具调用] get_server_logs('{server_ip}', {time_range_minutes})")
    print(f"  模拟从服务器 {server_ip} 拉取最近{time_range_minutes}分钟的日志...")

    # 生成模拟日志
    logs = generate_nginx_logs_for_server(server_ip, time_range_minutes)

    print(f"  共获取 {len(logs)} 条日志记录")
    if logs:
        print(f"  最后一条日志时间: {logs[-1].split('[')[1].split(']')[0] if '[' in logs[-1] else 'N/A'}")

    return logs


@tool("根据服务器IP获取服务指标")
def get_server_metrics(server_ip: str, time_range_minutes: int = 60) -> Dict[str, Any]:
    """
    获取指定服务器的性能监控指标。

    参数:
        server_ip (str): 服务器IP地址
        time_range_minutes (int): 时间范围（分钟），默认60分钟

    返回:
        Dict: 包含成功率、延迟、CPU/内存使用率等指标的字典
    """
    print(f"\n[工具调用] get_server_metrics('{server_ip}', {time_range_minutes})")
    print(f"  模拟从服务器 {server_ip} 获取最近{time_range_minutes}分钟的指标...")

    # 生成模拟指标
    metrics = generate_metrics_for_server(server_ip, time_range_minutes)

    print(f"  指标概况:")
    print(f"  - 成功率: {metrics['success_rate']:.1%}")
    print(f"  - 平均延迟: {metrics['avg_latency_ms']:.1f}ms")
    print(f"  - P95延迟: {metrics['p95_latency_ms']:.1f}ms")
    print(f"  - CPU使用率: {metrics['cpu_percent']:.1f}%")
    print(f"  - 内存使用率: {metrics['memory_percent']:.1f}%")

    return metrics


# 可选：报告生成工具
@tool("生成诊断报告")
def generate_diagnosis_report(api_endpoint: str, log_analysis: str, metrics_analysis: str) -> str:
    """
    根据日志和指标分析结果生成诊断报告。

    参数:
        api_endpoint (str): 被诊断的API端点
        log_analysis (str): 日志分析结果
        metrics_analysis (str): 指标分析结果

    返回:
        str: 格式化的诊断报告
    """
    print(f"\n[工具调用] generate_diagnosis_report('{api_endpoint}')")

    report = f"""# 故障诊断报告

## 诊断目标
- **接口**: {api_endpoint}
- **问题**: 成功率下降
- **诊断时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 日志分析结果
{log_analysis}

## 指标分析结果  
{metrics_analysis}

## 综合诊断结论
（此处由根因诊断官智能体填写）

## 建议的排查步骤
1. 检查相关服务器的系统资源使用情况
2. 验证数据库连接池状态
3. 检查下游依赖服务健康状态
4. 查看最近是否有代码部署或配置变更
"""

    print("  诊断报告模板生成完成")
    return report