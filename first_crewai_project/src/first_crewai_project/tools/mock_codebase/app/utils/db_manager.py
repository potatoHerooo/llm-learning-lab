"""
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
