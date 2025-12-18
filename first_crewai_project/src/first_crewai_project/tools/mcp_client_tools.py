# tools/mcp_client_tools.py
"""
方案一（稳定版）：不再二次包装 Tool
直接把 mock_tools 里的 Tool 导出给 crew.py 使用
"""

from mock_tools import (
    get_nginx_servers,
    get_server_logs_simple as get_server_logs,
    get_server_metrics_simple as get_server_metrics,
    get_mysql_logs_simple,
    get_redis_logs_simple,
)

__all__ = [
    "get_nginx_servers",
    "get_server_logs",
    "get_server_metrics",
    "get_mysql_logs_simple",
    "get_redis_logs_simple",
]
