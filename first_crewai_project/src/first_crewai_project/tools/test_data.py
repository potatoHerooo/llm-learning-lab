#!/usr/bin/env python3
"""
测试数据生成模块 - 生成模拟的服务器、日志和指标数据
"""
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json


def generate_servers() -> List[Dict[str, Any]]:
    """
    生成模拟的服务器列表
    """
    servers = [
        {
            "ip": "10.0.1.101",
            "hostname": "web-server-01",
            "role": "web_frontend",
            "region": "us-east-1",
            "status": "healthy"
        },
        {
            "ip": "10.0.1.102",
            "hostname": "web-server-02",
            "role": "web_frontend",
            "region": "us-east-1",
            "status": "healthy"
        },
        {
            "ip": "10.0.2.101",
            "hostname": "api-server-01",
            "role": "api_backend",
            "region": "us-west-2",
            "status": "degraded"  # 模拟有问题的服务器
        },
        {
            "ip": "10.0.2.102",
            "hostname": "api-server-02",
            "role": "api_backend",
            "region": "us-west-2",
            "status": "healthy"
        },
        {
            "ip": "10.0.3.101",
            "hostname": "db-server-01",
            "role": "database",
            "region": "eu-central-1",
            "status": "healthy"
        }
    ]
    return servers


def generate_nginx_logs_for_server(server_ip: str, time_range_minutes: int = 60) -> List[str]:
    """
    为指定服务器生成模拟的Nginx access_log日志

    生成不同类型的错误日志：
    - 5xx错误：服务器内部错误
    - 4xx错误：客户端错误
    - 慢请求：延迟过高
    - 正常请求：用于对比
    """
    logs = []

    # 确定当前时间
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=time_range_minutes)

    # 根据服务器IP决定错误类型
    if server_ip == "10.0.2.101":  # 有问题的服务器
        error_ratio = 0.4  # 40%的错误率
        error_types = ["502", "500", "499", "200"]  # 包含各种错误码
    else:
        error_ratio = 0.05  # 5%的错误率
        error_types = ["200", "404", "500"]  # 主要是正常请求

    # 时间戳步进（假设每分钟有多个请求）
    time_step = time_range_minutes * 60 / 100  # 生成100条日志

    for i in range(100):
        # 计算日志时间
        log_time = start_time + timedelta(seconds=i * time_step)
        timestamp = log_time.strftime('%d/%b/%Y:%H:%M:%S +0000')

        # 随机决定是否生成错误
        if random.random() < error_ratio:
            status_code = random.choice(["502", "500", "504", "499"])
            response_time = random.uniform(2.0, 10.0)  # 慢响应
        else:
            status_code = "200"
            response_time = random.uniform(0.05, 0.5)  # 正常响应

        # 随机API端点
        endpoints = [
            "/api/v2/data.json",
            "/api/v1/users",
            "/api/v1/products",
            "/static/js/app.js",
            "/health"
        ]
        request_path = random.choice(endpoints)

        # HTTP方法
        method = random.choice(["GET", "POST"])

        # 客户端IP
        client_ips = ["192.168.1." + str(random.randint(1, 255)) for _ in range(5)]
        client_ip = random.choice(client_ips)

        # 生成日志行 (Nginx combined格式)
        log_line = f'{client_ip} - - [{timestamp}] "{method} {request_path} HTTP/1.1" {status_code} {random.randint(100, 5000)} "-" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" {response_time:.3f}'

        logs.append(log_line)

    # 添加一些特定的错误模式（针对问题API）
    if server_ip == "10.0.2.101":
        # 在特定时间点添加错误激增
        error_time = start_time + timedelta(minutes=30)
        timestamp = error_time.strftime('%d/%b/%Y:%H:%M:%S +0000')
        for _ in range(10):  # 10个连续的502错误
            log_line = f'192.168.10.100 - - [{timestamp}] "GET /api/v2/data.json HTTP/1.1" 502 0 "-" "Python-urllib/3.9" 8.456'
            logs.append(log_line)

    # 按时间排序
    logs.sort()

    return logs


def generate_metrics_for_server(server_ip: str, time_range_minutes: int = 60) -> Dict[str, Any]:
    """
    为指定服务器生成模拟的性能指标
    """
    # 基础指标
    if server_ip == "10.0.2.101":  # 有问题的服务器
        # 模拟问题服务器的指标
        success_rate = random.uniform(0.6, 0.8)  # 60-80%成功率
        avg_latency = random.uniform(800, 1500)  # 高延迟
        cpu_percent = random.uniform(85, 98)  # 高CPU使用率
        memory_percent = random.uniform(90, 95)  # 高内存使用率
    else:
        # 正常服务器的指标
        success_rate = random.uniform(0.98, 0.995)  # 98-99.5%成功率
        avg_latency = random.uniform(50, 200)  # 正常延迟
        cpu_percent = random.uniform(30, 60)  # 正常CPU使用率
        memory_percent = random.uniform(40, 70)  # 正常内存使用率

    metrics = {
        "server_ip": server_ip,
        "timestamp": datetime.now().isoformat(),
        "time_range_minutes": time_range_minutes,

        # 成功率相关指标
        "success_rate": success_rate,
        "error_rate": 1 - success_rate,
        "total_requests": random.randint(10000, 50000),
        "failed_requests": int((1 - success_rate) * random.randint(10000, 50000)),

        # 延迟指标
        "avg_latency_ms": avg_latency,
        "p50_latency_ms": avg_latency * 0.7,
        "p95_latency_ms": avg_latency * 1.8,
        "p99_latency_ms": avg_latency * 2.5,

        # 系统资源指标
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
        "disk_io_percent": random.uniform(5, 30),
        "network_rx_mbps": random.uniform(10, 100),
        "network_tx_mbps": random.uniform(5, 50),

        # 应用特定指标
        "active_connections": random.randint(100, 500),
        "thread_pool_size": random.randint(50, 200),
        "queue_length": random.randint(0, 50),

        # 依赖服务健康状态
        "database_connections": random.randint(10, 100),
        "database_latency_ms": random.uniform(10, 100),
        "cache_hit_rate": random.uniform(0.7, 0.95),

        # 时间序列数据点（简化的）
        "timeline": [
            {"time_offset": -60, "success_rate": success_rate - 0.1 if server_ip == "10.0.2.101" else 0.99},
            {"time_offset": -30, "success_rate": success_rate - 0.2 if server_ip == "10.0.2.101" else 0.98},
            {"time_offset": 0, "success_rate": success_rate}
        ]
    }

    return metrics


def save_test_data_to_file():
    """
    将测试数据保存到文件，方便查看和调试
    """
    print("生成测试数据并保存到文件...")

    # 生成数据
    servers = generate_servers()
    logs = generate_nginx_logs_for_server("10.0.2.101", 60)
    metrics = generate_metrics_for_server("10.0.2.101", 60)

    # 保存到文件
    with open("test_servers.json", "w") as f:
        json.dump(servers, f, indent=2, default=str)

    with open("test_logs.txt", "w") as f:
        f.write("\n".join(logs))

    with open("test_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    print("测试数据已保存:")
    print("  - test_servers.json: 服务器列表")
    print("  - test_logs.txt: Nginx日志示例")
    print("  - test_metrics.json: 性能指标示例")


if __name__ == "__main__":
    # 直接运行此文件可以生成测试数据
    save_test_data_to_file()