
#!/usr/bin/env python3
"""
模拟工具模块 - 为故障诊断智能体提供模拟数据
"""
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple
import os
import re
import json
from typing import Dict, List, Any, Optional, Tuple
# 假设的代码仓库路径
CODE_BASE_PATH = "/mnt/codebase"  # 你可以修改为实际路径或使用环境变量


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

# 尝试导入 MySQL mock 数据生成器
try:
    from mysql_test_data import generate_mysql_logs_for_server
except ImportError:
    import sys, os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from mysql_test_data import generate_mysql_logs_for_server

# 尝试导入 Redis mock 数据生成器
try:
    from redis_test_data import generate_redis_logs_for_server
except ImportError:
    import sys, os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from redis_test_data import generate_redis_logs_for_server

# ==================== 原始函数（不装饰）====================

def get_nginx_servers_raw() -> List[Dict[str, Any]]:
    """获取所有Nginx服务器的IP地址和基本信息。"""
    print(f"[工具调用] get_nginx_servers() - 获取服务器列表")
    servers = generate_servers()
    print(f"  找到 {len(servers)} 台服务器:")
    for server in servers:
        print(f"  - {server['ip']} ({server['role']}, 区域: {server['region']})")
    return servers


def get_server_logs_simple_raw(
        server_ip: str,
        api_endpoint: str = None,
        keywords: Union[str, List[str]] = None
) -> List[Dict[str, Any]]:
    """
    获取服务器日志（Nginx），并输出统一日志结构 UnifiedLogV1：
    根据【关键词或者时间戳】【分批】搜索出来
    {
        "source": "nginx",
        "server_ip": "...",
        "timestamp": "...",
        "severity": "...",
        "operation": "GET /api/v2/data.json",
        "status": "502",
        "latency_ms": 200.5,
        "raw": "原始日志"
    }
    """
    print(f"[工具调用] get_server_logs_simple('{server_ip}', api_endpoint={api_endpoint}, keywords={keywords})")

    # 生成日志
    logs = generate_nginx_logs_for_server(server_ip, 60)

    # 按 接口路径 过滤
    if api_endpoint:
        logs = [log for log in logs if api_endpoint in log]

    # 按关键词过滤：不区分大小写
    if keywords:
        if isinstance(keywords, str):
            keywords = [keywords]

        logs = [
            log for log in logs
            if any(k.lower() in log.lower() for k in keywords)
        ]

    print(f"[工具调用] 找到 {len(logs)} 条相关日志")

    # 解析 Nginx 日志 → 统一结构 UnifiedLogV1
    structured_logs = []

    for log in logs[:10]:  # 仍然只处理前10条，避免LLM负载过大
        try:
            import re

            # 路径
            path_match = re.search(r'"(GET|POST)\s+([^\s?]+)', log)
            method = path_match.group(1) if path_match else "UNKNOWN"
            path = path_match.group(2) if path_match else "unknown"

            # 状态码
            status_match = re.search(r'"\s+(\d{3})\s+', log)
            status_code = status_match.group(1) if status_match else "000"

            # 响应时间
            rt_match = re.search(r'([\d.]+)$', log)
            response_time = float(rt_match.group(1)) if rt_match else 0.0
            latency_ms = response_time * 1000

            # IP
            ip_match = re.match(r'(\S+)', log)
            client_ip = ip_match.group(1) if ip_match else "0.0.0.0"

            # 时间戳
            time_match = re.search(r'\[(.*?)\]', log)
            timestamp = time_match.group(1) if time_match else ""

            # 统一结构 UnifiedLogV1
            structured_logs.append({
                "source": "nginx",
                "server_ip": server_ip,
                "timestamp": timestamp,
                "severity": "ERROR" if int(status_code) >= 500 else "INFO",
                "operation": f"{method} {path}",
                "status": status_code,
                "latency_ms": latency_ms,
                "raw": log
            })

        except Exception as e:
            print(f"[警告] 解析日志失败: {e}")
            continue

    return structured_logs


def get_mysql_logs_simple_raw(
        server_ip: str,
        start_time: str = "",
        end_time: str = "",
        keywords: str = "",
        min_duration_s: float = 0.0,
        limit: int = 1000
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    获取 MySQL 日志（模拟），并解析为统一日志结构 UnifiedLogV1 格式。
    """
    print(f"[工具调用] get_mysql_logs_simple - server_ip: {server_ip}")

    # 处理 keywords 参数
    keywords_list = []
    if keywords:
        if isinstance(keywords, list):
            keywords = ",".join(str(k) for k in keywords)
            print(f"[调试] 自动转换 keywords 为字符串: {keywords}")
        keywords_list = [k.strip() for k in keywords.split(",") if k.strip()]

    # 确保其他参数有合理的默认值
    start_time = start_time if start_time else None
    end_time = end_time if end_time else None
    min_duration_s_val = float(min_duration_s) if min_duration_s else 0.0

    print(
        f"  参数: start_time={start_time}, end_time={end_time}, keywords={keywords_list}, min_duration_s={min_duration_s_val}, limit={limit}")

    # 修复这里：安全地处理 min_duration_s 比较
    if min_duration_s is not None:
        min_duration_s_val = float(min_duration_s) if min_duration_s else 0.0
    else:
        min_duration_s_val = None

    # 原有的生成和解析逻辑保持不变...
    # 1. 生成日志（原始字符串）
    raw_logs = generate_mysql_logs_for_server(server_ip, 60)

    # 辅助函数：解析时间字符串（支持多种格式）
    def parse_time_string(time_str: str) -> Optional[datetime]:
        """解析时间字符串，支持多种格式"""
        if not time_str:
            return None

        try:
            if 'T' in time_str:
                time_str = time_str.replace('T', ' ')
                if '.' in time_str:
                    time_str = time_str.split('.')[0]
        except Exception:
            pass

        try:
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                return datetime.fromisoformat(time_str)
            except Exception:
                print(f"[警告] 无法解析时间格式: {time_str}")
                return None

    # 辅助函数：解析日志时间戳
    def parse_ts(log: str) -> Optional[datetime]:
        try:
            ts_str = log[:19]  # 假设格式为 "YYYY-MM-DD HH:MM:SS"
            return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None

    # 关键词过滤
    if keywords_list:
        raw_logs = [log for log in raw_logs if any(k.lower() in log.lower() for k in keywords_list)]

    # 最小耗时过滤（筛选慢 SQL）
    if min_duration_s_val and min_duration_s_val > 0:
        filtered = []
        for log in raw_logs:
            import re
            duration_match = re.search(r'duration=([\d.]+)s', log)
            if duration_match:
                duration = float(duration_match.group(1))
                if duration >= min_duration_s_val:
                    filtered.append(log)
        raw_logs = filtered

    # 时间窗过滤（限流）
    if start_time:
        start_dt = parse_time_string(start_time)
        if start_dt:
            raw_logs = [log for log in raw_logs if parse_ts(log) and parse_ts(log) >= start_dt]

    if end_time:
        end_dt = parse_time_string(end_time)
        if end_dt:
            raw_logs = [log for log in raw_logs if parse_ts(log) and parse_ts(log) <= end_dt]

    # 排序，将所有日志按照时间戳升序排序
    raw_logs.sort(key=lambda x: parse_ts(x) or datetime.min)
    print(f"[工具调用] 找到 {len(raw_logs)} 条 MySQL 日志")

    # 解析 → 统一结构 UnifiedLogV1 → 并只筛选limit条日志
    batch_logs = raw_logs[:limit]
    structured_logs = []
    next_start_time = None

    for log in batch_logs:
        try:
            import re
            # 时间戳
            ts = log[:19]
            # 严重级别
            sev_match = re.search(r"\[(INFO|WARN|ERROR)\]", log)
            severity = sev_match.group(1) if sev_match else "INFO"

            # SQL
            sql_match = re.search(r'sql="([^"]+)"', log)
            sql = sql_match.group(1) if sql_match else "UNKNOWN SQL"

            # 耗时
            dur_match = re.search(r'duration=([\d.]+)s', log)
            latency_ms = float(dur_match.group(1)) * 1000 if dur_match else 0.0

            status = "ERROR" if severity == "ERROR" else "OK"

            structured_logs.append({
                "source": "mysql",
                "server_ip": server_ip,
                "timestamp": ts,
                "severity": severity,
                "operation": sql,
                "status": status,
                "latency_ms": latency_ms,
                "raw": log
            })

            next_start_time = ts

        except Exception as e:
            print(f"[警告] 解析 MySQL 日志失败: {e}")
            continue

    # 检查是否还有下一页
    if len(batch_logs) < limit:
        next_start_time = None

    return structured_logs, next_start_time


def mysql_runtime_diagnosis_raw(
        server_ip: str,
        action: str,
) -> Dict[str, Any]:
    """
    MySQL 运行时诊断工具（模拟）
    """
    print(f"[工具调用] mysql_runtime_diagnosis(server_ip={server_ip}, action={action})")

    if action == "processlist":
        return {
            "type": "processlist",
            "processes": [
                {
                    "id": 1234,
                    "user": "app_user",
                    "db": "order_db",
                    "time_sec": 85,
                    "state": "Waiting for lock",
                    "sql": "UPDATE orders SET status='PAID' WHERE id=10001"
                },
                {
                    "id": 1235,
                    "user": "report_user",
                    "db": "order_db",
                    "time_sec": 2,
                    "state": "Sending data",
                    "sql": "SELECT * FROM orders WHERE created_at > NOW() - INTERVAL 1 DAY"
                }
            ]
        }

    elif action == "innodb_status":
        return {
            "type": "innodb_status",
            "latest_deadlock": {
                "transaction_1": "UPDATE orders SET status='PAID' WHERE id=10001",
                "transaction_2": "UPDATE orders SET status='CANCEL' WHERE id=10001",
                "locked_table": "orders",
                "locked_index": "PRIMARY",
                "note": "两个事务互相等待行锁，产生死锁"
            }
        }
    elif action == "variables":
        return {
            "type": "variables",
            "slow_query_log": "ON",
            "slow_query_log_file": "/var/log/mysql/slow.log",
            "long_query_time": 2,
            "max_connections": 500
        }

    elif action == "connections":
        return {
            "type": "connections",
            "threads_connected": 480,
            "threads_running": 120,
            "max_connections": 500,
            "warning": "连接数接近上限"
        }

    else:
        return {
            "error": f"不支持的诊断动作: {action}"
        }


def get_redis_logs_simple_raw(
    server_ip: str,
    keywords: Optional[Union[str, List[str]]] = None,
    min_duration: Optional[float] = None,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    获取 Redis 日志并解析成 UnifiedLogV1 格式
    """
    print(f"[工具调用] get_redis_logs_simple('{server_ip}', keywords={keywords}, min_duration_s={min_duration})")

    logs = generate_redis_logs_for_server(server_ip, 60)

    # 关键词过滤
    if keywords:
        if isinstance(keywords, str):
            keywords = [keywords]
        logs = [log for log in logs if any(k.lower() in log.lower() for k in keywords)]

    # 最小耗时过滤
    if min_duration:
        filtered = []
        for log in logs:
            import re
            dur_match = re.search(r'duration=(\d+)ms', log)
            if dur_match:
                dur_ms = int(dur_match.group(1))
                if dur_ms >= min_duration * 1000:
                    filtered.append(log)
        logs = filtered

    # 统一结构化
    structured = []
    import re

    for log in logs[:15]:
        try:
            ts = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", log).group(1)
            severity = re.search(r"\[(INFO|WARN|ERROR|SLOWLOG)\]", log).group(1)

            cmd_match = re.search(r'command="([^"]+)"', log)
            command = cmd_match.group(1) if cmd_match else "UNKNOWN"

            dur_match = re.search(r'duration=(\d+)ms', log)
            latency_ms = int(dur_match.group(1)) if dur_match else 0

            status = "ERROR" if "ERROR" in severity else "OK"

            structured.append({
                "source": "redis",
                "server_ip": server_ip,
                "timestamp": ts,
                "severity": severity,
                "operation": command,
                "status": status,
                "latency_ms": latency_ms,
                "raw": log
            })

        except Exception as e:
            print(f"[警告] Redis 日志解析失败: {e}")
            continue

    return structured


def get_server_metrics_simple_raw(
        server_ip: str,
        metric_name: Union[str, List[str]] = None
) -> Dict[str, Any]:
    """
    简化的指标获取工具，支持批量查询和智能名称映射。
    """
    print(f"[工具调用] get_server_metrics_simple('{server_ip}', metric_name={metric_name})")

    # 生成所有模拟指标
    all_metrics = generate_metrics_for_server(server_ip, 60)

    # 简化的指标名称映射表
    metric_mapping = {
        # CPU相关
        "cpu": "cpu_percent",
        "cpu_usage": "cpu_percent",
        "cpu_percent": "cpu_percent",
        "cpu_load": "cpu_percent",

        # 内存相关
        "memory": "memory_percent",
        "memory_usage": "memory_percent",
        "memory_percent": "memory_percent",
        "ram_usage": "memory_percent",

        # 成功率相关
        "success_rate": "success_rate",
        "request_success_rate": "success_rate",
        "success": "success_rate",

        # 延迟相关
        "latency": "avg_latency_ms",
        "avg_latency": "avg_latency_ms",
        "response_time": "avg_latency_ms",
        "avg_response_time": "avg_latency_ms",

        # 连接数相关
        "active_connections": "active_connections",
        "connections": "active_connections",
        "connection_count": "active_connections",

        # 其他常用别名
        "requests_per_sec": "requests_per_sec",
        "rps": "requests_per_sec",
        "qps": "requests_per_sec",
        "throughput": "requests_per_sec",

        "error_rate": "error_rate",
        "failure_rate": "error_rate",
    }

    # 添加 error_rate（如果不存在）
    if "error_rate" not in all_metrics and "success_rate" in all_metrics:
        all_metrics["error_rate"] = 100 - all_metrics["success_rate"]

    # 1. 如果 metric_name 为 None，返回所有指标
    if metric_name is None:
        print(f"  未指定指标名称，返回所有 {len(all_metrics)} 个指标")
        return all_metrics

    # 2. 处理字符串类型的 metric_name
    elif isinstance(metric_name, str):
        # 特殊关键字 "all" 仍然支持
        if metric_name.lower() == "all":
            print(f"  关键字 'all'，返回所有 {len(all_metrics)} 个指标")
            return all_metrics

        # 尝试映射指标名称
        actual_key = metric_mapping.get(metric_name, metric_name)

        if actual_key in all_metrics:
            return {actual_key: all_metrics[actual_key]}
        else:
            # 返回可用指标列表和建议
            available_metrics = list(all_metrics.keys())
            return {
                "error": f"指标 '{metric_name}' 不存在",
                "available_metrics": available_metrics,
                "common_aliases": {
                    "cpu": ["cpu_usage", "cpu_percent"],
                    "memory": ["memory_usage", "memory_percent"],
                    "success_rate": ["request_success_rate"],
                    "latency": ["avg_latency_ms", "response_time"]
                }
            }

    # 3. 处理列表类型的 metric_name（批量查询）
    elif isinstance(metric_name, list):
        result = {}
        not_found = []

        for name in metric_name:
            if isinstance(name, str):
                # 映射指标名称
                mapped_key = metric_mapping.get(name, name)

                if mapped_key in all_metrics:
                    result[mapped_key] = all_metrics[mapped_key]
                else:
                    result[name] = "指标不存在"
                    not_found.append(name)

        print(f"  批量查询 {len(metric_name)} 个指标，成功获取 {len(result) - len(not_found)} 个")

        response = {
            "server_ip": server_ip,
            "metrics": result,
            "total_requested": len(metric_name),
            "found": len(result) - len(not_found),
            "not_found": not_found if not_found else None,
            "timestamp": datetime.now().isoformat()
        }

        return response

    # 4. 其他类型
    else:
        return {
            "error": f"不支持的 metric_name 类型: {type(metric_name)}",
            "supported_types": ["str", "list", "None"],
            "examples": {
                "获取所有指标": {"metric_name": None},
                "获取单个指标": {"metric_name": "cpu_percent"},
                "获取多个指标": {"metric_name": ["cpu_percent", "memory_percent", "success_rate"]}
            }
        }

def search_code_in_repository_raw(
        file_pattern: str = "*.py",
        keyword: str = None,
        file_path: str = None
) -> Dict[str, Any]:
    """
    在代码仓库中搜索特定文件或包含关键字的代码

    Args:
        file_pattern: 文件模式，如 "*.py", "*.java"
        keyword: 搜索的关键字
        file_path: 直接指定文件路径（如果有）

    Returns:
        搜索结果的字典
    """
    # 新增：处理智能体可能传入的列表参数
    import json
    import sys

    # 如果传入的是字符串，尝试解析为JSON
    if isinstance(file_pattern, str) and file_pattern.startswith('['):
        try:
            params_list = json.loads(file_pattern)
            # 取第一个参数集合
            if params_list and isinstance(params_list, list) and len(params_list) > 0:
                first_params = params_list[0]
                file_pattern = first_params.get('file_pattern', "*.py")
                keyword = first_params.get('keyword', keyword)
                file_path = first_params.get('file_path', file_path)
        except:
            pass  # 如果解析失败，保持原样

    print(
        f"[工具调用] search_code_in_repository(file_pattern={file_pattern}, keyword={keyword}, file_path={file_path})")

    # 如果是直接指定文件路径，直接返回该文件
    if file_path:
        if os.path.exists(file_path):
            return {
                "type": "direct_file",
                "file_path": file_path,
                "exists": True,
                "suggestions": [f"已定位到文件: {file_path}"]
            }
        else:
            # 尝试在代码仓库中查找
            file_path = os.path.join(CODE_BASE_PATH, file_path.lstrip('/'))
            if os.path.exists(file_path):
                return {
                    "type": "direct_file",
                    "file_path": file_path,
                    "exists": True,
                    "suggestions": [f"已定位到文件: {file_path}"]
                }

    # 模拟搜索结果 - 实际项目中应该遍历目录
    results = []

    # 根据接口路径猜测可能的代码文件
    if keyword and "/api/" in keyword:
        # 从API路径推断代码文件
        api_path = keyword
        # 例如: /api/v2/data.json -> controllers/data_controller.py, views/data_view.py 等
        parts = api_path.strip('/').split('/')
        if len(parts) >= 2:
            endpoint = parts[-1].replace('.json', '').replace('.', '_')

            # 生成可能的文件路径
            possible_files = [
                f"app/controllers/{endpoint}_controller.py",
                f"app/api/v{parts[1] if parts[1].startswith('v') and len(parts) > 1 else '1'}/{endpoint}.py",
                f"src/routes/{endpoint}_routes.py",
                f"api/views/{endpoint}_view.py",
                f"handlers/{endpoint}_handler.py"
            ]

            for file in possible_files:
                full_path = os.path.join(CODE_BASE_PATH, file)
                results.append({
                    "file_path": file,
                    "full_path": full_path,
                    "confidence": "high",
                    "reason": f"根据API路径 {api_path} 推断"
                })

    # 根据关键字搜索（模拟）
    if keyword:
        # 模拟常见问题的代码文件
        common_problem_files = {
            "timeout": [
                {"file": "app/services/order_service.py", "line": 45, "code": "time.sleep(5)"},
                {"file": "app/utils/network_utils.py", "line": 78, "code": "requests.get(url, timeout=None)"}
            ],
            "memory": [
                {"file": "app/utils/cache_manager.py", "line": 120, "code": "cache = []  # 内存泄漏风险"},
                {"file": "app/services/data_service.py", "line": 33,
                 "code": "data_list = []\nwhile True:\n    data_list.append(get_data())"}
            ],
            "deadlock": [
                {"file": "app/services/payment_service.py", "line": 67,
                 "code": "with lock1:\n    with lock2:\n        # 处理支付"},
                {"file": "app/utils/db_manager.py", "line": 89,
                 "code": "session1.query(User).filter(User.id==1).with_for_update()"}
            ],
            "502": [
                {"file": "app/controllers/api_controller.py", "line": 112,
                 "code": "response = requests.get('http://downstream-service')"},
                {"file": "app/middlewares/error_handler.py", "line": 56,
                 "code": "if status_code >= 500:\n    return '502 Bad Gateway'"}
            ]
        }

        for problem_type, files in common_problem_files.items():
            if problem_type in keyword.lower():
                for file_info in files:
                    results.append({
                        "file_path": file_info["file"],
                        "full_path": os.path.join(CODE_BASE_PATH, file_info["file"]),
                        "confidence": "medium",
                        "reason": f"常见{problem_type}问题相关文件",
                        "line": file_info["line"],
                        "sample_code": file_info["code"]
                    })

    # 如果没有找到具体结果，返回通用建议
    if not results:
        results = [
            {
                "file_path": "app/controllers/",
                "full_path": os.path.join(CODE_BASE_PATH, "app/controllers"),
                "confidence": "low",
                "reason": "建议检查控制器目录"
            },
            {
                "file_path": "app/services/",
                "full_path": os.path.join(CODE_BASE_PATH, "app/services"),
                "confidence": "low",
                "reason": "建议检查服务层代码"
            }
        ]

    return {
        "search_results": results,
        "total_count": len(results),
        "keyword": keyword,
        "file_pattern": file_pattern
    }


def get_code_context_raw(
        file_path: str,
        line_start: int = 1,
        line_end: int = 50,
        highlight_lines: List[int] = None
) -> Dict[str, Any]:
    """
    获取代码文件的上下文内容

    Args:
        file_path: 文件路径
        line_start: 起始行号
        line_end: 结束行号
        highlight_lines: 需要高亮显示的行号列表

    Returns:
        代码内容和元数据
    """
    print(f"[工具调用] get_code_context(file_path={file_path}, line_start={line_start}, line_end={line_end})")

    # 处理相对路径
    if not os.path.isabs(file_path):
        file_path = os.path.join(CODE_BASE_PATH, file_path.lstrip('/'))

    # 检查文件是否存在
    if not os.path.exists(file_path):
        return {
            "error": f"文件不存在: {file_path}",
            "suggestions": [
                f"请检查文件路径是否正确",
                f"可以尝试使用 search_code_in_repository 工具搜索"
            ]
        }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total_lines = len(lines)

        # 确保行号在有效范围内
        line_start = max(1, min(line_start, total_lines))
        line_end = max(line_start, min(line_end, total_lines))

        # 获取指定行范围内的代码
        code_snippet = lines[line_start - 1:line_end]

        # 构建行号映射
        code_with_lines = []
        for i, line in enumerate(code_snippet, start=line_start):
            is_highlighted = highlight_lines and i in highlight_lines
            code_with_lines.append({
                "line_number": i,
                "content": line.rstrip('\n'),
                "highlighted": is_highlighted
            })

        # 分析代码特征（简单版）
        issues = []
        for i, line_info in enumerate(code_with_lines):
            line = line_info["content"]

            # 检查常见问题模式
            if "time.sleep(" in line and "time.sleep(0.1)" not in line:
                issues.append({
                    "line": line_info["line_number"],
                    "type": "性能问题",
                    "description": "长时间sleep可能导致请求超时",
                    "severity": "high"
                })

            if "while True:" in line and "break" not in "".join([l["content"] for l in code_with_lines[i:i + 10]]):
                issues.append({
                    "line": line_info["line_number"],
                    "type": "无限循环风险",
                    "description": "可能缺少循环终止条件",
                    "severity": "high"
                })

            if "requests.get(" in line and "timeout=" not in line:
                issues.append({
                    "line": line_info["line_number"],
                    "type": "网络请求超时",
                    "description": "缺少timeout参数可能导致请求挂起",
                    "severity": "medium"
                })

            if "session.query(" in line and ".all()" in line:
                issues.append({
                    "line": line_info["line_number"],
                    "type": "数据库查询优化",
                    "description": "考虑使用分页查询避免内存溢出",
                    "severity": "medium"
                })

        return {
            "file_path": file_path,
            "total_lines": total_lines,
            "line_start": line_start,
            "line_end": line_end,
            "code": code_with_lines,
            "issues_found": issues,
            "language": "python" if file_path.endswith('.py') else
            "java" if file_path.endswith('.java') else
            "javascript" if file_path.endswith('.js') else "unknown"
        }

    except Exception as e:
        return {
            "error": f"读取文件失败: {str(e)}",
            "file_path": file_path
        }


def analyze_code_pattern_raw(
        code_snippet: str,
        issue_type: str = None
) -> Dict[str, Any]:
    """
    分析代码片段，识别常见问题模式

    Args:
        code_snippet: 代码片段
        issue_type: 指定要分析的问题类型（可选）

    Returns:
        分析结果
    """
    print(f"[工具调用] analyze_code_pattern(issue_type={issue_type})")

    # 常见问题模式检测
    patterns = {
        "memory_leak": [
            # 使用非贪婪匹配 .*? 避免匹配过多
            (r"\.append\(.*?\)\s*# 没有清理", "列表不断追加可能导致内存泄漏"),
            (r"global\s+\w+\s*=\s*\[\]", "全局变量累积数据"),
            (r"while True:\s*\n\s*\w+\.append", "循环中不断追加到列表"),
            # 修正：使用 [^)]* 匹配括号内任意非右括号字符
            (r"PIL\.Image\.new\([^)]*\)\s*# 没有关闭", "图片资源未释放"),
            # 还可以添加更多常见内存泄漏模式：
            (r"open\([^)]*\)\s*(#.*)?$", "文件打开后没有关闭"),
            (r"connection\s*=\s*.+\.connect\(\)", "数据库连接没有关闭"),
            (r"self\.cache\s*=\s*{}\s*# 无限增长", "缓存字典无限增长"),
            (r"\.add\(.*?\)\s*# 集合不断添加", "集合不断添加元素"),
            (r"threading\.Thread\(target=.*\)", "线程没有正确管理")
        ],
        "deadlock": [
            (r"with lock[12]:\s*\n\s*with lock[21]:", "嵌套锁可能导致死锁"),
            (r"lock\.acquire\(\)\s*\n.*lock\.acquire\(\)", "重复获取锁"),
            (r"threading\.Lock\(\)\s*# 多线程死锁风险", "多线程同步问题")
        ],
        "timeout": [
            (r"time\.sleep\([5-9]\)", "长时间sleep"),
            (r"requests\.\w+\([^)]*timeout=None", "网络请求未设置超时"),
            (r"while True:\s*if.*break", "可能无法退出的循环"),
            (r"socket\.settimeout\(None\)", "socket未设置超时")
        ],
        "database": [
            (r"\.all\(\)\s*# 查询所有数据", "未分页的全表查询"),
            (r"N\+1\s+query", "N+1查询问题"),
            (r"SELECT \*\s+FROM", "SELECT * 性能问题"),
            (r"for.*in.*:\s*\n\s*session\.add", "循环中逐个插入数据")
        ],
        "security": [
            (r"eval\(", "使用eval有安全风险"),
            (r"exec\(", "使用exec有安全风险"),
            (r"subprocess\.call\(.*shell=True", "shell命令注入风险"),
            (r"password\s*=\s*['\"]\w+['\"]", "硬编码密码")
        ]
    }

    findings = []

    # 如果没有指定问题类型，检查所有类型
    issue_types_to_check = [issue_type] if issue_type else patterns.keys()

    for check_type in issue_types_to_check:
        if check_type in patterns:
            for pattern, description in patterns[check_type]:
                matches = re.finditer(pattern, code_snippet, re.MULTILINE)
                for match in matches:
                    # 获取匹配的行
                    line_start = code_snippet[:match.start()].count('\n') + 1
                    line_content = match.group(0).strip()

                    findings.append({
                        "issue_type": check_type,
                        "line": line_start,
                        "pattern": pattern,
                        "description": description,
                        "matched_code": line_content,
                        "severity": "high" if check_type in ["memory_leak", "deadlock"] else "medium"
                    })

    # 如果没有找到特定问题，进行通用分析
    if not findings:
        # 检查代码复杂度
        lines = code_snippet.split('\n')

        # 计算一些基本指标
        metrics = {
            "line_count": len(lines),
            "function_count": len(re.findall(r"def \w+", code_snippet)),
            "class_count": len(re.findall(r"class \w+", code_snippet)),
            "import_count": len(re.findall(r"import |from ", code_snippet)),
            "comment_ratio": sum(1 for line in lines if line.strip().startswith('#')) / len(lines) if lines else 0
        }

        # 简单复杂度分析
        if metrics["line_count"] > 100:
            findings.append({
                "issue_type": "complexity",
                "description": "代码文件过长，建议拆分",
                "severity": "low",
                "metrics": metrics
            })

    return {
        "analysis_type": issue_type or "general",
        "findings": findings,
        "total_issues_found": len(findings),
        "summary": "发现{}个潜在问题".format(len(findings)) if findings else "未发现明显问题"
    }

# ==================== 使用@tool装饰的版本（供CrewAI使用）====================
from crewai.tools import tool

@tool("获取Nginx服务器列表")
def get_nginx_servers() -> List[Dict[str, Any]]:
    """获取所有Nginx服务器的IP地址和基本信息。"""
    return get_nginx_servers_raw()


@tool("获取服务器日志")
def get_server_logs_simple(
        server_ip: str,
        api_endpoint: str = None,
        keywords: Union[str, List[str]] = None
) -> List[Dict[str, Any]]:
    """获取服务器日志（Nginx），并输出统一日志结构 UnifiedLogV1"""
    return get_server_logs_simple_raw(server_ip, api_endpoint, keywords)


@tool("获取MySQL日志")
def get_mysql_logs_simple(
        server_ip: str,
        start_time: str = "",
        end_time: str = "",
        keywords: str = "",
        min_duration_s: float = 0.0,
        limit: int = 1000
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """获取 MySQL 日志（模拟），并解析为统一日志结构 UnifiedLogV1 格式。"""
    return get_mysql_logs_simple_raw(server_ip, start_time, end_time, keywords, min_duration_s, limit)


@tool("MYSQL运行时诊断")
def mysql_runtime_diagnosis(
        server_ip: str,
        action: str,
) -> Dict[str, Any]:
    """MySQL 运行时诊断工具（模拟）"""
    return mysql_runtime_diagnosis_raw(server_ip, action)


@tool("获取Redis日志")
def get_redis_logs_simple(
    server_ip: str,
    keywords: Optional[Union[str, List[str]]] = None,
    min_duration: Optional[float] = None,
    **kwargs
) -> List[Dict[str, Any]]:
    """获取 Redis 日志并解析成 UnifiedLogV1 格式"""
    return get_redis_logs_simple_raw(server_ip, keywords, min_duration, **kwargs)

@tool("获取服务器指标")
def get_server_metrics_simple(
        server_ip: str,
        metric_name: Union[str, List[str]] = None
) -> Dict[str, Any]:
    """简化的指标获取工具，支持批量查询和智能名称映射。"""
    return get_server_metrics_simple_raw(server_ip, metric_name)

@tool("搜索代码仓库")
def search_code_in_repository(
        file_pattern: str = "*.py",
        keyword: str = None,
        file_path: str = None
) -> Dict[str, Any]:
    """在代码仓库中搜索特定文件或包含关键字的代码"""
    return search_code_in_repository_raw(file_pattern, keyword, file_path)


@tool("获取代码上下文")
def get_code_context(
        file_path: str,
        line_start: int = 1,
        line_end: int = 50,
        highlight_lines: List[int] = None
) -> Dict[str, Any]:
    """获取代码文件的上下文内容"""
    return get_code_context_raw(file_path, line_start, line_end, highlight_lines)


@tool("分析代码模式")
def analyze_code_pattern(
        code_snippet: str,
        issue_type: str = None
) -> Dict[str, Any]:
    """分析代码片段，识别常见问题模式"""
    return analyze_code_pattern_raw(code_snippet, issue_type)
# ==================== 测试函数 ====================

def test_tools_locally():
    """本地测试工具函数"""
    print("🔧 本地测试工具函数")

    # 测试服务器列表
    servers = get_nginx_servers_raw()
    print(f"获取到 {len(servers)} 台服务器")

    # 测试获取特定服务器的日志
    test_server = "10.0.2.101"
    print(f"\n测试服务器 {test_server} 的日志:")
    logs = get_server_logs_simple_raw(test_server, api_endpoint="/api/v2/data.json")
    print(f"获取到 {len(logs)} 条日志")

    if logs:
        for log in logs[:3]:
            print(f"  - 严重级别: {log['severity']}, 操作: {log['operation']}")

    # 测试获取指标
    print(f"\n测试服务器 {test_server} 的指标:")
    metrics = get_server_metrics_simple_raw(test_server, metric_name="cpu")
    print(f"CPU使用率: {metrics.get('cpu_percent', 'N/A')}%")

    print("\n✅ 本地测试完成")


# ==================== 使用@tool装饰的版本（供CrewAI使用）====================

if __name__ == "__main__":
    test_tools_locally()
