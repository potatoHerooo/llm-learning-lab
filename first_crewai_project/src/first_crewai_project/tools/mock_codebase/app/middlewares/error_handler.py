"""
错误处理中间件
处理应用中的各种错误
"""

import time
import traceback
from flask import jsonify, request, g
import logging

class ErrorHandler:
    def __init__(self, app=None):
        self.app = app
        self.error_counts = {}  # 错误计数

    def init_app(self, app):
        """初始化应用"""
        self.app = app

        # 注册错误处理器
        @app.errorhandler(400)
        def handle_bad_request(error):
            return self._format_error(400, "Bad Request", error)

        @app.errorhandler(404)
        def handle_not_found(error):
            return self._format_error(404, "Not Found", error)

        @app.errorhandler(500)
        def handle_internal_error(error):
            # 记录错误详情
            self._log_error(500, error)
            return self._format_error(500, "Internal Server Error", error)

        @app.errorhandler(502)
        def handle_bad_gateway(error):
            # 502错误特殊处理
            return self._handle_502(error)

    def _format_error(self, code: int, message: str, error: Exception):
        """格式化错误响应"""
        error_info = {
            "error": {
                "code": code,
                "message": message,
                "path": request.path,
                "timestamp": time.time(),
                "request_id": getattr(g, 'request_id', None)
            }
        }

        # 问题：生产环境不应返回堆栈跟踪
        if self.app and self.app.debug:
            error_info["error"]["traceback"] = traceback.format_exc()

        # 增加错误计数
        self._increment_error_count(code)

        return jsonify(error_info), code

    def _handle_502(self, error: Exception):
        """处理502错误"""
        # 问题：没有降级策略
        error_info = {
            "error": {
                "code": 502,
                "message": "Bad Gateway",
                "description": "无法连接到下游服务",
                "suggestion": "请稍后重试",
                "timestamp": time.time()
            }
        }

        # 记录502错误
        logging.error(f"502错误: {request.url} - {str(error)}")

        # 问题：错误计数可能无限增长
        self._increment_error_count(502)

        return jsonify(error_info), 502

    def _increment_error_count(self, code: int):
        """增加错误计数"""
        if code not in self.error_counts:
            self.error_counts[code] = 0

        self.error_counts[code] += 1

        # 问题：从不清理旧计数
        # 应该定期清理或设置上限

    def _log_error(self, code: int, error: Exception):
        """记录错误"""
        logging.error(f"错误 {code}: {str(error)}")

        # 问题：同步写入日志文件（性能差）
        with open("error_logs.txt", "a") as f:
            f.write(f"{time.time()}: {code} - {str(error)}\n")

    def get_error_stats(self):
        """获取错误统计"""
        return self.error_counts

# 全局错误处理器
error_handler = ErrorHandler()
