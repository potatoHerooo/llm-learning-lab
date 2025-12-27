"""
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
