"""
日志中间件
记录请求和响应日志
"""

import time
import json
from flask import request, g
import logging

class RequestLogger:
    def __init__(self):
        self.log_queue = []  # 内存中的日志队列

    def log_request(self, request):
        """记录请求"""
        start_time = time.time()

        request_info = {
            "method": request.method,
            "path": request.path,
            "query_string": request.query_string.decode('utf-8') if request.query_string else "",
            "client_ip": request.remote_addr,
            "user_agent": request.user_agent.string,
            "start_time": start_time,
            "request_id": id(request)  # 简单请求ID
        }

        # 保存到g对象
        g.request_info = request_info
        g.start_time = start_time

        # 问题：同步记录日志（影响性能）
        logging.info(f"请求开始: {request.method} {request.path}")

        # 添加到内存队列（可能内存泄漏）
        self.log_queue.append(request_info)

        # 清理旧日志（但可能不执行）
        if len(self.log_queue) > 1000:
            self.log_queue = self.log_queue[-500:]  # 只保留最近500条

    def log_response(self, response):
        """记录响应"""
        if hasattr(g, 'start_time'):
            elapsed = time.time() - g.start_time

            response_info = {
                "status_code": response.status_code,
                "elapsed": elapsed,
                "end_time": time.time()
            }

            # 慢请求警告
            if elapsed > 2.0:
                logging.warning(f"慢请求: {request.path} - {elapsed:.3f}s")

            # 添加到内存队列
            if hasattr(g, 'request_info'):
                log_entry = {**g.request_info, **response_info}
                self.log_queue.append(log_entry)

            # 同步写入文件（性能差）
            self._write_to_file(response_info)

    def _write_to_file(self, response_info):
        """写入文件"""
        try:
            with open("request_logs.txt", "a") as f:
                f.write(json.dumps(response_info) + "\n")
        except Exception as e:
            logging.error(f"写入日志失败: {e}")

    def get_logs(self, limit=100):
        """获取日志"""
        return self.log_queue[-limit:]

# 全局日志记录器
request_logger = RequestLogger()
