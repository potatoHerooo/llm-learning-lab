# redis_test_data.py
import random
from datetime import datetime, timedelta
from typing import List

REDIS_COMMANDS = [
    'GET user:1',
    'GET user:10',
    'SET user:3 1',
    'HGETALL cart:22',
    'LPUSH queue:task 1001',
    'INCR counter:login',
    'DEL session:33',
]

REDIS_ERRORS = [
    "timeout",
    "connection lost",
    "OOM command not allowed",
    "key not found",
    "cluster down",
]


def generate_redis_logs_for_server(server_ip: str, time_range_minutes: int = 60) -> List[str]:
    logs = []
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=time_range_minutes)

    log_count = 60
    time_step = time_range_minutes * 60 / log_count

    for i in range(log_count):
        ts = start_time + timedelta(seconds=i * time_step)
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")

        cmd = random.choice(REDIS_COMMANDS)
        p = random.random()

        # 10% error
        if p < 0.10:
            err = random.choice(REDIS_ERRORS)
            log = f'{ts_str} [ERROR] error="{err}" command="{cmd}"'

        # 20% slow command
        elif p < 0.30:
            dur = random.randint(50, 500)
            log = f'{ts_str} [SLOWLOG] duration={dur}ms command="{cmd}"'

        # 20% warn
        elif p < 0.50:
            log = f'{ts_str} [WARN] command="{cmd}"'

        # normal
        else:
            log = f'{ts_str} [INFO] command="{cmd}"'

        logs.append(log)

    # 某些 Redis 服务器可以人为“增强错误”
    if server_ip.endswith("101"):
        extra_ts = end_time.strftime("%Y-%m-%d %H:%M:%S")
        logs.append(f'{extra_ts} [ERROR] error="timeout" command="GET hot:key"')

    return logs
