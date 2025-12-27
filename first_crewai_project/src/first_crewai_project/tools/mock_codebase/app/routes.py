"""
应用路由配置
包含路由定义和中间件配置
智能体搜索的第三个文件
"""

from flask import Flask, request, g, jsonify
import time
from app.controllers.data_controller import DataController
from app.api.v2.data import data_bp
from app.middlewares.auth import auth_middleware
from app.middlewares.logging import request_logger

def create_app():
    """创建Flask应用"""
    app = Flask(__name__)

    # 配置
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

    # 注册中间件
    @app.before_request
    def before_request():
        """请求前中间件"""
        g.start_time = time.time()

        # 问题：每个请求都创建数据库连接
        from app.utils.db_manager import DatabaseManager
        g.db = DatabaseManager()

        # 问题：每个请求都创建Redis连接
        from app.utils.redis_client import RedisClient
        g.redis = RedisClient()

        # 记录请求
        request_logger.log_request(request)

    @app.after_request
    def after_request(response):
        """请求后中间件"""
        # 计算请求耗时
        if hasattr(g, 'start_time'):
            elapsed = time.time() - g.start_time
            response.headers['X-Response-Time'] = f'{elapsed:.3f}s'

            # 慢请求日志
            if elapsed > 2.0:
                app.logger.warning(f"慢请求: {request.path} - {elapsed:.3f}s")

        # 问题：连接没有关闭
        # if hasattr(g, 'db'):
        #     g.db.close()  # 缺少这行代码

        # if hasattr(g, 'redis'):
        #     g.redis.close()  # 缺少这行代码

        return response

    @app.errorhandler(502)
    def handle_502(error):
        """502错误处理"""
        app.logger.error(f"502错误: {request.url} - {str(error)}")

        # 问题：没有降级策略，直接返回错误
        return jsonify({
            "error": "Bad Gateway",
            "message": "无法连接下游服务",
            "path": request.path,
            "timestamp": time.time()
        }), 502

    @app.errorhandler(504)
    def handle_504(error):
        """504错误处理"""
        app.logger.error(f"504错误: {request.url} - {str(error)}")

        # 问题：网关超时没有重试机制
        return jsonify({
            "error": "Gateway Timeout",
            "message": "请求处理超时",
            "suggestion": "请稍后重试"
        }), 504

    # 注册蓝图
    app.register_blueprint(data_bp)

    # 注册控制器路由
    data_controller = DataController()

    @app.route('/api/v1/data', methods=['GET'])
    def get_data_v1():
        """V1数据接口（兼容旧版）"""
        # 问题：V1接口仍然在使用，但可能有问题
        return data_controller.get_data_v2()  # 实际上调用V2逻辑

    @app.route('/api/v1/data/<int:data_id>', methods=['PUT'])
    def update_data_v1(data_id):
        """更新数据（V1）"""
        # 问题：没有版本控制，直接调用控制器
        return data_controller.update_data(data_id)

    @app.route('/health', methods=['GET'])
    def health_check():
        """健康检查"""
        # 问题：健康检查也创建数据库连接
        try:
            from app.utils.db_manager import DatabaseManager
            db = DatabaseManager()
            db.execute("SELECT 1")

            from app.utils.redis_client import RedisClient
            redis = RedisClient()
            redis.ping()

            return jsonify({"status": "healthy"})
        except Exception as e:
            app.logger.error(f"健康检查失败: {e}")
            return jsonify({"status": "unhealthy", "error": str(e)}), 500

    @app.route('/metrics', methods=['GET'])
    def metrics():
        """应用指标"""
        import psutil
        import threading

        metrics_data = {
            "memory": psutil.virtual_memory().percent,
            "cpu": psutil.cpu_percent(interval=1),
            "threads": threading.active_count(),
            "uptime": time.time() - app.start_time if hasattr(app, 'start_time') else 0
        }

        # 问题：每次调用都收集大量指标
        # 收集所有线程信息（可能泄漏敏感信息）
        threads_info = []
        for thread in threading.enumerate():
            threads_info.append({
                "name": thread.name,
                "daemon": thread.daemon,
                "alive": thread.is_alive()
            })

        metrics_data["threads_detail"] = threads_info

        return jsonify(metrics_data)

    # 记录应用启动时间
    app.start_time = time.time()

    return app

# 全局应用实例
app = create_app()

if __name__ == '__main__':
    # 问题：开发服务器配置不当
    app.run(
        host='0.0.0.0',  # 允许所有IP访问
        port=5000,
        debug=True,  # 生产环境不应开启debug
        threaded=True  # 多线程模式，但可能产生线程安全问题
    )
