#!/usr/bin/env python3
"""
模拟 MySQL 日志生成模块，用于 AIOps 故障诊断系统
生成 slow log / error log 风格的 MySQL 日志
"""

import random
from datetime import datetime, timedelta
from typing import List


MYSQL_QUERIES = [
    "SELECT * FROM users WHERE id=3;",
    "UPDATE products SET stock = stock - 1 WHERE id=10;",
    "INSERT INTO orders (user_id, amount) VALUES (2, 199.99);",
    "DELETE FROM carts WHERE user_id = 8;",
    "SELECT * FROM payments WHERE status='FAILED';",
    "SELECT COUNT(*) FROM logs WHERE level='ERROR';"
]

ERROR_TYPES = [
    "Deadlock found when trying to get lock",
    "Table doesn't exist",
    "Syntax error near 'FROM'",
    "Lock wait timeout exceeded",
    "Too many connections"
]


def generate_mysql_logs_for_server(server_ip: str, time_range_minutes: int = 60) -> List[str]:
    """
    生成 MySQL 日志：
    - INFO：正常查询
    - WARN：慢查询 / 死锁
    - ERROR：SQL 执行失败

    返回内容为原始 MySQL 日志字符串列表
    """

    logs = []

    #从当前出错误时间一个小时之内出现错误的日志
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=time_range_minutes)

    # 日志数量固定 80 条，这个可以根据需要调整
    log_count = 80
    time_step = time_range_minutes * 60 / log_count


    #SQL日志示例：
    # timestamp: 2024-01-01 10:00:01
    # query: [ERROR] [Query] duration=3.2s
    # sql: SELECT * FROM users WHERE id=3;
    for i in range(log_count):
        # ------------------------------
        # ① 时间部分
        # ------------------------------
        timestamp = start_time + timedelta(seconds=i * time_step)
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")

        # ------------------------------
        # ② 错误类型 + 耗时 + SQL语句
        # ------------------------------
        query = random.choice(MYSQL_QUERIES)

        # 随机决定该日志的类型（正常 / 慢 / 错误）
        p = random.random()

        # 10% 概率：错误日志
        if p < 0.10:
            error = random.choice(ERROR_TYPES)
            log = (
                f"{timestamp_str} [ERROR] [Query] duration=0s "
                f"sql=\"{query}\" error=\"{error}\""
            )

        # 20% 概率：死锁或警告
        elif p < 0.30:
            duration = round(random.uniform(1.0, 3.0), 2)
            log = (
                f"{timestamp_str} [WARN] [Deadlock] duration={duration}s "
                f"sql=\"{query}\" msg=\"Transaction deadlock occurred\""
            )

        # 30% 概率：慢查询（> 1s）
        elif p < 0.60:
            duration = round(random.uniform(1.0, 5.0), 2)
            log = (
                f"{timestamp_str} [WARN] [SlowQuery] duration={duration}s "
                f"sql=\"{query}\""
            )

        # 剩下 40%：正常查询
        else:
            duration = round(random.uniform(0.01, 0.3), 3)
            log = (
                f"{timestamp_str} [INFO] [Query] duration={duration}s "
                f"sql=\"{query}\""
            )

        logs.append(log)

    # 让 server_ip 特定服务器更容易生成异常
    if server_ip.endswith("101"):  # 例如 10.0.3.101 是 database server
        extra_error_time = start_time + timedelta(minutes=time_range_minutes // 2)
        ts = extra_error_time.strftime("%Y-%m-%d %H:%M:%S")
        logs.append(f"{ts} [ERROR] [Query] duration=0s sql=\"SELECT * FROM users;\" error=\"Too many connections\"")

    return logs
