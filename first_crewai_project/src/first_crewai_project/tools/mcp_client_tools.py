
"""
MCP Tool Bridge - 简化版本

直接使用原始函数，避免@tool装饰器的问题
"""

from crewai.tools import tool
from mock_tools import (
    get_nginx_servers_raw,
    get_server_logs_simple_raw,
    get_server_metrics_simple_raw,
    get_mysql_logs_simple_raw,
    mysql_runtime_diagnosis_raw,
    get_redis_logs_simple_raw
)

# 简单包装函数，直接调用原始函数
@tool("获取Nginx服务器列表")
def get_nginx_servers():
    """获取所有 Nginx 服务器列表。"""
    return get_nginx_servers_raw()


@tool("获取服务器日志")
def get_server_logs(server_ip: str, api_endpoint: str = None, keywords=None):
    """获取指定服务器的 Nginx 日志。"""
    # 处理keywords参数，确保是正确格式
    if isinstance(keywords, str):
        # 如果keywords是字符串，保持原样
        pass
    elif isinstance(keywords, list):
        # 如果keywords是列表，转换为字符串
        keywords = ",".join(str(k) for k in keywords)
    
    return get_server_logs_simple_raw(
        server_ip=server_ip,
        api_endpoint=api_endpoint,
        keywords=keywords
    )


@tool("获取服务器指标")
def get_server_metrics(server_ip: str, metric_name: str = None):
    """获取服务器性能指标。"""
    return get_server_metrics_simple_raw(
        server_ip=server_ip,
        metric_name=metric_name
    )


@tool("获取MySQL日志")
def get_mysql_logs_simple(server_ip: str, keywords: str = "", min_duration_s: float = 0.0):
    """获取 MySQL 日志。"""
    # 注意：这里只传递必要的参数，其他参数使用默认值
    logs, next_time = get_mysql_logs_simple_raw(
        server_ip=server_ip,
        keywords=keywords,
        min_duration_s=min_duration_s
    )
    return logs


@tool("MYSQL运行时诊断")
def mysql_runtime_diagnosis(server_ip: str, action: str):
    """MySQL 运行时诊断。"""
    return mysql_runtime_diagnosis_raw(
        server_ip=server_ip,
        action=action
    )


@tool("获取Redis日志")
def get_redis_logs_simple(server_ip: str, keywords=None, min_duration=None):
    """获取 Redis 日志。"""
    return get_redis_logs_simple_raw(
        server_ip=server_ip,
        keywords=keywords,
        min_duration=min_duration
    )
