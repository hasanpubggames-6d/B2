import time
import redis.asyncio as redis
import os

class RateLimiter:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis = redis.from_url(redis_url)

    async def is_allowed(self, user_id: int, limit: int = 5, period: int = 60) -> bool:
        """
        Check if user is within rate limits.
        """
        key = f"rate_limit:{user_id}"
        current = await self.redis.get(key)
        
        if current is None:
            await self.redis.set(key, 1, ex=period)
            return True
        
        if int(current) < limit:
            await self.redis.incr(key)
            return True
        
        return False

    async def cache_result(self, key: str, value: str, expire: int = 3600):
        await self.redis.set(f"cache:{key}", value, ex=expire)

    async def get_cached(self, key: str) -> str:
        return await self.redis.get(f"cache:{key}")
