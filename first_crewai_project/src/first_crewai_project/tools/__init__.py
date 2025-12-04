#!/usr/bin/env python3
"""
工具模块包

__init__.py是整个工具箱的目录和说明书

第一部分：从子模块导入函数
    - 这样导入之后，这些函数就成为tools包的直接成员
第二部分：定义__all__列表
    - 定义了当使用 from tools import * 之后，哪些名称会被导出

具体功能：简化导入 直接from tools import get_nginx_servers
    如果没有整个文件的话，导入语句需要写成：from tools.mock_tools import get_nginx_servers
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