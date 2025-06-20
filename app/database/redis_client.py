"""
Redis客户端配置
"""
import json
import redis.asyncio as redis
from typing import Any, Optional
from app.core.config import settings

class RedisClient:
    def __init__(self):
        self.redis_pool = None
        
    async def connect(self):
        """连接Redis"""
        try:
            self.redis_pool = redis.ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True,
                max_connections=20
            )
            # 测试连接
            client = redis.Redis(connection_pool=self.redis_pool)
            await client.ping()
            print("✅ Redis连接成功")
            return True
        except Exception as e:
            print(f"❌ Redis连接失败: {e}")
            return False
    
    async def get_client(self):
        """获取Redis客户端"""
        if not self.redis_pool:
            await self.connect()
        return redis.Redis(connection_pool=self.redis_pool)
    
    async def set(self, key: str, value: Any, expire: int = 3600):
        """设置缓存"""
        client = await self.get_client()
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        await client.set(key, value, ex=expire)
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        client = await self.get_client()
        value = await client.get(key)
        if value is None:
            return None
        
        # 尝试解析JSON
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    async def delete(self, key: str):
        """删除缓存"""
        client = await self.get_client()
        await client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        client = await self.get_client()
        return await client.exists(key)
    
    async def expire(self, key: str, seconds: int):
        """设置过期时间"""
        client = await self.get_client()
        await client.expire(key, seconds)
    
    async def increment(self, key: str, amount: int = 1):
        """递增计数器"""
        client = await self.get_client()
        return await client.incr(key, amount)
    
    async def set_hash(self, name: str, mapping: dict, expire: int = 3600):
        """设置哈希表"""
        client = await self.get_client()
        await client.hset(name, mapping=mapping)
        await client.expire(name, expire)
    
    async def get_hash(self, name: str, key: str = None):
        """获取哈希表数据"""
        client = await self.get_client()
        if key:
            return await client.hget(name, key)
        return await client.hgetall(name)
    
    async def add_to_set(self, key: str, *values):
        """添加到集合"""
        client = await self.get_client()
        await client.sadd(key, *values)
    
    async def get_set_members(self, key: str):
        """获取集合成员"""
        client = await self.get_client()
        return await client.smembers(key)
    
    async def close(self):
        """关闭连接"""
        if self.redis_pool:
            await self.redis_pool.disconnect()

# 全局Redis客户端实例
redis_client = RedisClient()

# 测试Redis连接
async def test_redis_connection():
    """测试Redis连接"""
    return await redis_client.connect()

# 同步测试函数
def sync_test_redis():
    """同步测试Redis连接"""
    import asyncio
    return asyncio.run(test_redis_connection())