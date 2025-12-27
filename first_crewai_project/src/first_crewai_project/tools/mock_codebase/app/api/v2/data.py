"""
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
