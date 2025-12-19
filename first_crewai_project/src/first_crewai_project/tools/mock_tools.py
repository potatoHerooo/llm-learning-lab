
#!/usr/bin/env python3
"""
模拟工具模块 - 为故障诊断智能体提供模拟数据
"""
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple

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
        metric_name: str = None
) -> Dict[str, Any]:
    """
    简化的指标获取工具，避免复杂的参数验证问题。
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
        metric_name: str = None
) -> Dict[str, Any]:
    """简化的指标获取工具，避免复杂的参数验证问题。"""
    return get_server_metrics_simple_raw(server_ip, metric_name)


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


if __name__ == "__main__":
    test_tools_locally()
