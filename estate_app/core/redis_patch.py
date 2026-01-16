import sys

import redis.asyncio as redis


def setup_redis():
    sys.modules["aioredis"] = redis
    sys.modules["aioredis.client"] = redis
    sys.modules["aioredis.connection"] = redis
