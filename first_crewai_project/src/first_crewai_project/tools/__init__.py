#!/usr/bin/env python3
"""
工具模块包
"""
from .mock_tools import (
    get_nginx_servers,
    get_server_logs,
    get_server_metrics,
    generate_diagnosis_report
)

from .test_data import (
    generate_servers,
    generate_nginx_logs_for_server,
    generate_metrics_for_server,
    save_test_data_to_file
)

__all__ = [
    'get_nginx_servers',
    'get_server_logs',
    'get_server_metrics',
    'generate_diagnosis_report',
    'generate_servers',
    'generate_nginx_logs_for_server',
    'generate_metrics_for_server',
    'save_test_data_to_file'
]