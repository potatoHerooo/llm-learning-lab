"""
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
            f.write(json.dumps(log_entry) + "
")

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
