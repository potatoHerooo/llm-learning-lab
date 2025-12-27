"""
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
