# mock_problem_files_agent_focused.py
"""
根据智能体实际搜索路径创建模拟文件
智能体实际在寻找：
1. app/controllers/data_controller.py
2. app/api/v2/data.py
3. app/routes.py 或类似路由文件
"""

import os
from pathlib import Path

CODE_BASE_PATH = "./mock_codebase"  # 修改为你的项目路径


def create_agent_focused_files():
    """创建智能体实际在寻找的文件"""

    # 智能体第一个想看的文件
    controller_file = os.path.join(CODE_BASE_PATH, "app/controllers/data_controller.py")
    os.makedirs(os.path.dirname(controller_file), exist_ok=True)

    with open(controller_file, 'w') as f:
        f.write('''"""
数据控制器 - 处理 /api/v2/data.json 相关请求
智能体第一优先级文件
包含502错误、慢查询和死锁问题
"""

from flask import jsonify, request, abort
import time
import requests
from app.services.data_service import DataService
from app.utils.redis_client import RedisClient
from app.utils.db_manager import DatabaseManager

class DataController:
    def __init__(self):
        self.data_service = DataService()
        self.redis_client = RedisClient()
        self.db_manager = DatabaseManager()

        # 全局缓存（可能内存泄漏）
        self.request_cache = []  # 问题：从不清理的缓存

    def get_data_v2(self):
        """
        处理 GET /api/v2/data.json 请求
        这是导致502错误的主要函数
        """
        try:
            # 问题1: 调用下游服务没有超时设置
            downstream_url = "http://internal-data-service/api/raw"
            print(f"调用下游服务: {downstream_url}")

            # 危险：缺少timeout参数，可能导致永久阻塞
            response = requests.get(downstream_url)  # 没有设置timeout

            # 问题2: 错误处理不完整
            if response.status_code != 200:
                # 没有重试机制，直接返回错误
                return jsonify({"error": "下游服务异常", "code": 502}), 502

            data = response.json()

            # 问题3: 同步阻塞处理大数据
            processed_data = self._process_data_slowly(data)

            # 问题4: 没有缓存降级
            cache_key = "data_v2_cache"
            self.redis_client.set(cache_key, processed_data, expire=300)

            # 问题5: 向全局缓存添加数据（内存泄漏）
            self.request_cache.append({
                "timestamp": time.time(),
                "data_size": len(str(processed_data))
            })

            return jsonify(processed_data)

        except requests.exceptions.ConnectionError as e:
            print(f"连接错误: {e}")
            return jsonify({"error": "无法连接下游服务", "code": 502}), 502
        except Exception as e:
            print(f"未知错误: {e}")
            return jsonify({"error": "服务器内部错误", "code": 500}), 500

    def _process_data_slowly(self, data):
        """
        缓慢处理数据（性能瓶颈）
        包含多个性能问题
        """
        import json

        # 问题：同步JSON序列化大对象
        json_str = json.dumps(data)  # 如果data很大，这里会阻塞

        # 问题：CPU密集型操作没有优化
        result = []
        for i in range(len(data.get("items", []))):
            item = data["items"][i]

            # 嵌套循环（O(n^2)复杂度）
            for j in range(10):
                # 模拟复杂计算
                processed = self._heavy_computation(item, j)
                result.append(processed)

            # 问题：每次循环都查询数据库
            db_result = self.db_manager.query_item(item.get("id"))
            if db_result:
                result[-1]["db_info"] = db_result

        return {"items": result, "count": len(result)}

    def _heavy_computation(self, item, index):
        """CPU密集型计算"""
        import hashlib
        import random

        # 模拟耗时计算
        for _ in range(1000):
            hash_obj = hashlib.md5(str(item).encode())
            hash_obj.hexdigest()

        # 随机休眠（增加延迟）
        time.sleep(random.uniform(0.01, 0.05))

        return {"id": item.get("id"), "hash": hash_obj.hexdigest(), "index": index}

    def update_data(self, data_id):
        """
        更新数据（可能导致死锁）
        """
        from threading import Lock

        # 问题：全局锁可能导致死锁
        global_lock = Lock()
        db_lock = Lock()

        with global_lock:
            # 获取数据库连接
            with db_lock:
                # 查询当前数据
                current = self.db_manager.query(f"SELECT * FROM data WHERE id={data_id} FOR UPDATE")
                time.sleep(0.5)  # 模拟处理时间

                # 更新操作
                self.db_manager.execute(f"UPDATE data SET updated_at=NOW() WHERE id={data_id}")

                # 同时更新缓存（可能产生竞态条件）
                cache_key = f"data_{data_id}"
                self.redis_client.delete(cache_key)
                self.redis_client.set(cache_key, {"updated": True})

        return {"status": "success", "id": data_id}

    def batch_process(self, item_ids):
        """
        批量处理（N+1查询问题）
        """
        results = []

        # 问题：循环中查询数据库（N+1问题）
        for item_id in item_ids:
            # 每次循环都查询数据库
            item_data = self.db_manager.query(f"SELECT * FROM data WHERE id={item_id}")

            # 再次查询关联数据
            related = self.db_manager.query(
                f"SELECT * FROM related_data WHERE data_id={item_id}"
            )

            # 再次查询统计信息
            stats = self.db_manager.query(
                f"SELECT COUNT(*) as count FROM stats WHERE item_id={item_id}"
            )

            results.append({
                "item": item_data,
                "related": related,
                "stats": stats
            })

        # 正确做法应该是：使用JOIN一次性查询所有数据
        return results

# 全局变量（内存泄漏风险）
GLOBAL_DATA_BUFFER = []

def add_to_global_buffer(data):
    """向全局缓冲区添加数据，从不清理"""
    GLOBAL_DATA_BUFFER.append(data)

    # 记录日志（可能产生大量日志）
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.info(f"Added data to buffer, size: {len(GLOBAL_DATA_BUFFER)}")

    return len(GLOBAL_DATA_BUFFER)
''')

    # 智能体第二个想看的文件（注意：智能体写的是 vv2，应该是 v2）
    api_v2_file = os.path.join(CODE_BASE_PATH, "app/api/v2/data.py")
    os.makedirs(os.path.dirname(api_v2_file), exist_ok=True)

    with open(api_v2_file, 'w') as f:
        f.write('''"""
API v2 数据端点
智能体第二优先级文件
包含Redis缓存问题和连接池泄漏
"""

from flask import Blueprint, jsonify, request, current_app
import time
import json
import threading
from app.utils.redis_client import RedisClient

data_bp = Blueprint('data_v2', __name__, url_prefix='/api/v2')

@data_bp.route('/data', methods=['GET'])
def get_data():
    """
    GET /api/v2/data
    主要问题：Redis缓存使用不当
    """
    # 获取查询参数
    query = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    size = int(request.args.get('size', 100))

    # 问题1: 缓存键设计不当（可能导致大量不同的缓存键）
    cache_key = f"data_v2:{query}:{page}:{size}"

    redis_client = RedisClient()

    # 问题2: 缓存穿透 - 查询不存在的数据
    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return jsonify(json.loads(cached_data))
    except Exception as e:
        current_app.logger.error(f"Redis获取失败: {e}")
        # 没有降级策略，继续执行

    # 模拟数据库查询（慢查询）
    time.sleep(2.0)  # 超过慢查询阈值

    # 生成模拟数据
    data = {
        "query": query,
        "page": page,
        "size": size,
        "items": [{"id": i, "value": f"item_{i}"} for i in range(size)],
        "total": 1000
    }

    # 问题3: 缓存大对象（可能超过Redis内存限制）
    # 序列化整个大对象
    data_json = json.dumps(data)

    # 问题4: 缓存没有设置过期时间（有时设置了300秒，有时永久）
    if page == 1:
        redis_client.set(cache_key, data_json, expire=300)  # 5分钟
    else:
        redis_client.set(cache_key, data_json)  # 永久缓存，危险！

    # 问题5: 连接没有释放
    # redis_client.close()  # 缺少这行代码

    return jsonify(data)

@data_bp.route('/data/<int:data_id>', methods=['GET'])
def get_data_by_id(data_id):
    """
    获取单个数据
    问题：热点数据没有特殊处理
    """
    cache_key = f"data_item:{data_id}"

    redis_client = RedisClient()

    # 问题：缓存击穿 - 热点数据过期时大量请求直达数据库
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return jsonify(json.loads(cached))
    except:
        pass

    # 模拟数据库查询
    time.sleep(0.5)

    data = {
        "id": data_id,
        "name": f"Data Item {data_id}",
        "value": "x" * 1024,  # 大value
        "timestamp": time.time()
    }

    # 问题：热点数据设置相同的过期时间（可能导致缓存雪崩）
    import random
    expire_time = 300 + random.randint(-30, 30)  # 应该使用随机过期时间
    redis_client.set(cache_key, json.dumps(data), expire=expire_time)

    return jsonify(data)

@data_bp.route('/data', methods=['POST'])
def create_data():
    """
    创建数据
    问题：数据库事务和Redis不一致
    """
    data = request.json

    # 问题1: 先更新Redis，后更新数据库（不一致风险）
    redis_client = RedisClient()

    # 生成ID
    import uuid
    data_id = str(uuid.uuid4())
    data['id'] = data_id

    # 先缓存
    cache_key = f"data_item:{data_id}"
    redis_client.set(cache_key, json.dumps(data), expire=3600)

    # 然后数据库（可能失败）
    try:
        # 模拟数据库操作
        time.sleep(1.5)

        # 这里可能失败，但Redis已经更新了
        if "error" in data:
            raise Exception("模拟数据库错误")

        # 问题2: 没有清理相关缓存
        # 应该清理列表缓存，但没有做
        # redis_client.delete("data_v2:*")

        return jsonify({"status": "success", "id": data_id}), 201

    except Exception as e:
        # 数据库失败，但Redis已经更新（数据不一致）
        current_app.logger.error(f"数据库操作失败: {e}")
        return jsonify({"error": "创建失败"}), 500

# 后台任务线程（可能泄漏）
background_threads = []

def start_background_sync():
    """启动后台同步任务（线程泄漏）"""
    def sync_task():
        while True:
            try:
                # 执行同步
                sync_data()
                time.sleep(60)
            except Exception as e:
                current_app.logger.error(f"同步任务错误: {e}")
                time.sleep(10)

    # 创建线程但不记录引用
    thread = threading.Thread(target=sync_task, daemon=True)
    thread.start()

    # 问题：线程引用保存在全局列表，从不清理
    background_threads.append(thread)

    return len(background_threads)

def sync_data():
    """同步数据（可能产生死锁）"""
    # 模拟数据同步
    time.sleep(5)
    return True
''')

    # 智能体第三个想看的文件：routes.py
    routes_file = os.path.join(CODE_BASE_PATH, "app/routes.py")
    os.makedirs(os.path.dirname(routes_file), exist_ok=True)

    with open(routes_file, 'w') as f:
        f.write('''"""
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
''')

    # 创建服务层文件（智能体提到的 app/services/）
    service_file = os.path.join(CODE_BASE_PATH, "app/services/data_service.py")
    os.makedirs(os.path.dirname(service_file), exist_ok=True)

    with open(service_file, 'w') as f:
        f.write('''"""
数据服务层
包含业务逻辑和数据库操作
智能体搜索的服务层代码
"""

import time
import json
from typing import List, Dict, Any
from threading import Lock

class DataService:
    def __init__(self):
        self.cache = {}  # 本地缓存（可能内存泄漏）
        self.locks = {}  # 细粒度锁字典
        self.connection_pool = []  # 模拟连接池

        # 问题：全局统计列表
        self.request_stats = []  # 从不清理的统计数据

    def get_large_dataset(self, filters: Dict[str, Any]) -> List[Dict]:
        """
        获取大数据集（性能问题）
        """
        # 问题1: 全表扫描
        sql = "SELECT * FROM large_data_table"

        if filters:
            # 动态拼接SQL（SQL注入风险）
            conditions = []
            for key, value in filters.items():
                conditions.append(f"{key} = '{value}'")  # 字符串拼接，危险！

            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

        # 问题2: 没有分页
        sql += " ORDER BY created_at DESC"
        # 缺少 LIMIT 子句

        # 模拟执行慢查询
        time.sleep(3.0)  # 超过2秒的慢查询阈值

        # 返回大量数据
        result = []
        for i in range(10000):  # 模拟大数据量
            result.append({
                "id": i,
                "data": "x" * 1024,  # 每个记录1KB
                "timestamp": time.time()
            })

        # 问题3: 缓存大结果集
        cache_key = f"dataset:{str(filters)}"
        self.cache[cache_key] = result  # 缓存大对象

        return result

    def process_batch_transaction(self, items: List[Dict]) -> bool:
        """
        批量事务处理（死锁风险）
        """
        from app.utils.db_manager import DatabaseManager

        db = DatabaseManager()

        try:
            # 开始事务
            db.begin_transaction()

            # 问题：循环中执行数据库操作（性能差）
            for item in items:
                # 检查是否存在
                existing = db.query(f"SELECT id FROM items WHERE id={item['id']} FOR UPDATE")

                if existing:
                    # 更新（可能死锁）
                    db.execute(f"""
                        UPDATE items 
                        SET value='{item['value']}', updated_at=NOW() 
                        WHERE id={item['id']}
                    """)
                else:
                    # 插入
                    db.execute(f"""
                        INSERT INTO items (id, value) 
                        VALUES ({item['id']}, '{item['value']}')
                    """)

                # 问题：每次操作后都记录日志（I/O密集）
                self._log_operation(item)

                # 问题：小延迟增加死锁概率
                time.sleep(0.01)

            # 提交事务
            db.commit()
            return True

        except Exception as e:
            # 回滚
            db.rollback()
            print(f"事务失败: {e}")

            # 问题：没有重试机制
            return False

    def _log_operation(self, item: Dict):
        """记录操作日志（可能产生大量日志）"""
        log_entry = {
            "timestamp": time.time(),
            "operation": "process_item",
            "item_id": item.get("id"),
            "thread": threading.current_thread().name
        }

        # 添加到全局列表（内存泄漏）
        self.request_stats.append(log_entry)

        # 写入文件（同步I/O，性能差）
        with open("operation_logs.txt", "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def get_with_cache_through(self, key: str) -> Any:
        """
        缓存穿透问题示例
        """
        # 先查本地缓存
        if key in self.cache:
            return self.cache[key]

        # 查Redis
        from app.utils.redis_client import RedisClient
        redis = RedisClient()

        cached = redis.get(key)
        if cached:
            # 更新本地缓存
            self.cache[key] = json.loads(cached)
            return self.cache[key]

        # 查数据库（缓存穿透）
        from app.utils.db_manager import DatabaseManager
        db = DatabaseManager()

        result = db.query(f"SELECT * FROM cache_data WHERE cache_key='{key}'")

        if result:
            # 缓存结果
            redis.set(key, json.dumps(result), expire=300)
            self.cache[key] = result
            return result
        else:
            # 问题：查询不存在的数据，没有空值缓存
            return None  # 每次都会查询数据库

    def cleanup_old_data(self):
        """清理旧数据（可能长时间锁表）"""
        from app.utils.db_manager import DatabaseManager

        db = DatabaseManager()

        # 问题：DELETE without WHERE (危险，但这里是有WHERE)
        # 问题：大事务，可能锁表很久
        db.execute("""
            DELETE FROM old_data 
            WHERE created_at < NOW() - INTERVAL 90 DAY
        """)

        # 问题：没有LIMIT，可能删除大量数据
        # 问题：没有分批次删除

        time.sleep(10)  # 模拟长时间操作

        return True

# 全局服务实例（单例模式，但可能线程不安全）
_data_service_instance = None

def get_data_service():
    """获取数据服务实例（延迟初始化）"""
    global _data_service_instance

    if _data_service_instance is None:
        # 问题：没有锁，多线程可能创建多个实例
        _data_service_instance = DataService()

    return _data_service_instance
''')

    # 创建工具类文件
    utils_dir = os.path.join(CODE_BASE_PATH, "app/utils")
    os.makedirs(utils_dir, exist_ok=True)

    # Redis客户端
    redis_file = os.path.join(utils_dir, "redis_client.py")
    with open(redis_file, 'w') as f:
        f.write('''"""
Redis客户端工具
包含连接泄漏和配置问题
"""

import redis
import time
from typing import Optional, Any
import threading

class RedisClient:
    def __init__(self, host='localhost', port=6379, db=0):
        self.host = host
        self.port = port
        self.db = db

        # 问题：没有使用连接池
        self.connection = None

        # 问题：统计信息列表从不清理
        self.connection_stats = []

    def get_connection(self):
        """获取连接（连接泄漏）"""
        if self.connection is None or not self.connection.ping():
            # 每次创建新连接
            self.connection = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                socket_connect_timeout=5,
                socket_timeout=None  # 问题：没有设置socket超时
            )

        # 记录连接信息（内存泄漏）
        self.connection_stats.append({
            "timestamp": time.time(),
            "action": "get_connection"
        })

        return self.connection

    def get(self, key: str) -> Optional[str]:
        """获取值"""
        conn = self.get_connection()

        try:
            # 问题：没有重试机制
            value = conn.get(key)
            return value.decode('utf-8') if value else None
        except redis.exceptions.ConnectionError as e:
            print(f"Redis连接错误: {e}")
            return None
        except Exception as e:
            print(f"Redis操作错误: {e}")
            return None

    def set(self, key: str, value: Any, expire: Optional[int] = None):
        """设置值"""
        conn = self.get_connection()

        try:
            if expire:
                conn.setex(key, expire, value)
            else:
                conn.set(key, value)  # 永久缓存

            # 问题：没有返回值验证
            return True
        except Exception as e:
            print(f"Redis设置失败: {e}")
            return False

    def delete(self, key: str):
        """删除键"""
        conn = self.get_connection()

        try:
            conn.delete(key)
            return True
        except Exception as e:
            print(f"Redis删除失败: {e}")
            return False

    def pipeline(self):
        """流水线操作（可能阻塞）"""
        conn = self.get_connection()
        return conn.pipeline()

    def close(self):
        """关闭连接（通常不被调用）"""
        if self.connection:
            self.connection.close()
            self.connection = None

    def __del__(self):
        """析构函数（不一定被调用）"""
        try:
            self.close()
        except:
            pass

# 全局Redis连接（可能泄漏）
_global_redis = None

def get_redis():
    """获取全局Redis实例"""
    global _global_redis

    if _global_redis is None:
        _global_redis = RedisClient()

    return _global_redis

# 连接泄漏示例
class ConnectionLeakExample:
    def __init__(self):
        self.connections = []

    def leak_connections(self):
        """故意泄漏连接"""
        for i in range(100):
            conn = RedisClient()
            self.connections.append(conn)  # 保存引用，阻止垃圾回收
            # 不调用 conn.close()
''')

    # 数据库管理器
    db_file = os.path.join(utils_dir, "db_manager.py")
    with open(db_file, 'w') as f:
        f.write('''"""
数据库管理器
包含连接管理和查询问题
"""

import time
import threading
from typing import List, Dict, Any, Optional

class DatabaseManager:
    def __init__(self, max_connections=100):
        self.max_connections = max_connections
        self.connections = []  # 连接池
        self.active_connections = 0

        # 问题：全局锁，可能成为瓶颈
        self.lock = threading.Lock()

        # 问题：查询缓存（可能内存泄漏）
        self.query_cache = {}

    def get_connection(self):
        """获取数据库连接"""
        with self.lock:
            if len(self.connections) > 0:
                # 复用连接
                conn = self.connections.pop()
                self.active_connections += 1
                return conn
            elif self.active_connections < self.max_connections:
                # 创建新连接
                self.active_connections += 1
                return self._create_connection()
            else:
                # 问题：没有等待机制，直接抛异常
                raise Exception("数据库连接池耗尽")

    def _create_connection(self):
        """创建新连接（模拟）"""
        # 模拟连接创建耗时
        time.sleep(0.1)

        return {
            "id": threading.get_ident(),
            "created_at": time.time(),
            "last_used": time.time()
        }

    def release_connection(self, conn):
        """释放连接（可能不被调用）"""
        with self.lock:
            # 问题：连接可能已经无效，但没有检查
            self.connections.append(conn)
            self.active_connections -= 1

    def query(self, sql: str) -> List[Dict]:
        """执行查询"""
        conn = self.get_connection()

        try:
            # 问题：SQL注入风险（如果外部传入）
            # 问题：没有查询超时

            # 检查缓存（可能返回旧数据）
            cache_key = hash(sql)
            if cache_key in self.query_cache:
                # 问题：缓存没有过期时间
                cached = self.query_cache.get(cache_key)
                if time.time() - cached.get("cached_at", 0) < 60:
                    return cached.get("data", [])

            # 模拟查询耗时
            time.sleep(1.5)  # 慢查询

            # 模拟结果
            result = [{"id": i, "value": f"row_{i}"} for i in range(100)]

            # 更新缓存
            self.query_cache[cache_key] = {
                "data": result,
                "cached_at": time.time()
            }

            return result

        except Exception as e:
            print(f"查询失败: {e}")
            return []
        finally:
            # 问题：这里应该调用 release_connection，但可能忘记
            # self.release_connection(conn)
            pass

    def execute(self, sql: str) -> bool:
        """执行更新"""
        conn = self.get_connection()

        try:
            # 问题：没有事务管理
            # 问题：没有重试机制

            # 模拟执行耗时
            time.sleep(0.5)

            return True
        except Exception as e:
            print(f"执行失败: {e}")
            return False
        finally:
            # 同样的问题：连接可能没有释放
            pass

    def begin_transaction(self):
        """开始事务"""
        # 问题：没有实现嵌套事务
        pass

    def commit(self):
        """提交事务"""
        pass

    def rollback(self):
        """回滚事务"""
        pass

# 全局数据库连接（单例）
_global_db = None

def get_db():
    """获取全局数据库实例"""
    global _global_db

    if _global_db is None:
        _global_db = DatabaseManager()

    return _global_db

# 死锁示例
class DeadlockExample:
    def __init__(self):
        self.lock_a = threading.Lock()
        self.lock_b = threading.Lock()

    def method1(self):
        """可能产生死锁的方法1"""
        with self.lock_a:
            time.sleep(0.1)
            with self.lock_b:
                return "method1 done"

    def method2(self):
        """可能产生死锁的方法2（锁顺序相反）"""
        with self.lock_b:
            time.sleep(0.1)
            with self.lock_a:
                return "method2 done"
''')

    # 创建中间件目录和文件（智能体可能搜索的）
    middleware_dir = os.path.join(CODE_BASE_PATH, "app/middlewares")
    os.makedirs(middleware_dir, exist_ok=True)

    # 错误处理器
    error_file = os.path.join(middleware_dir, "error_handler.py")
    with open(error_file, 'w') as f:
        f.write('''"""
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
            f.write(f"{time.time()}: {code} - {str(error)}\\n")

    def get_error_stats(self):
        """获取错误统计"""
        return self.error_counts

# 全局错误处理器
error_handler = ErrorHandler()
''')

    # 日志中间件
    logging_file = os.path.join(middleware_dir, "logging.py")
    with open(logging_file, 'w') as f:
        f.write('''"""
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
                f.write(json.dumps(response_info) + "\\n")
        except Exception as e:
            logging.error(f"写入日志失败: {e}")

    def get_logs(self, limit=100):
        """获取日志"""
        return self.log_queue[-limit:]

# 全局日志记录器
request_logger = RequestLogger()
''')

    print("✅ 已根据智能体思路创建模拟文件：")
    print(f"   1. {controller_file}")
    print(f"   2. {api_v2_file}")
    print(f"   3. {routes_file}")
    print(f"   4. {service_file}")
    print(f"   5. {redis_file}")
    print(f"   6. {db_file}")
    print(f"   7. {error_file}")
    print(f"   8. {logging_file}")
    print("\n📁 文件结构：")
    print("   mock_codebase/")
    print("   ├── app/")
    print("   │   ├── controllers/")
    print("   │   │   └── data_controller.py")
    print("   │   ├── api/")
    print("   │   │   └── v2/")
    print("   │   │       └── data.py")
    print("   │   ├── services/")
    print("   │   │   └── data_service.py")
    print("   │   ├── utils/")
    print("   │   │   ├── redis_client.py")
    print("   │   │   └── db_manager.py")
    print("   │   ├── middlewares/")
    print("   │   │   ├── error_handler.py")
    print("   │   │   └── logging.py")
    print("   │   └── routes.py")


if __name__ == "__main__":
    # 创建模拟代码库
    create_agent_focused_files()

    print("\n🎯 创建完成！现在智能体可以：")
    print("   1. 搜索 'data_controller' → 找到 app/controllers/data_controller.py")
    print("   2. 搜索 'api/v2/data' → 找到 app/api/v2/data.py")
    print("   3. 搜索 'routes' → 找到 app/routes.py")
    print("   4. 搜索 'data_service' → 找到 app/services/data_service.py")
    print("\n🔍 每个文件都包含了智能体可能发现的问题：")
    print("   - 502错误（下游服务调用无超时）")
    print("   - 慢查询（SQL性能问题）")
    print("   - 死锁（并发控制问题）")
    print("   - 内存泄漏（全局变量、连接未释放）")
    print("   - Redis缓存问题（穿透、击穿、雪崩）")