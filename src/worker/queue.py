import json
import redis

from . import MQueue


class RedisQueue(MQueue):
    async def expired(self, key, ttl):
        self.client.expire(key, ttl)

    def __init__(self, host='localhost', port=6379, db=0):
        self.client = redis.StrictRedis(host=host, port=port, db=db)

    async def push(self, item, queue=None):
        if queue is not None:
            self.client.rpush(queue, json.dumps(item))
        else:
            self.client.rpush('queue', json.dumps(item))

    async def pop(self, queue=None):
        if queue is not None:
            item = self.client.blpop([queue], timeout=1)
        else:
            item = self.client.blpop(['queue'], timeout=1)

        if item is not None:
            return json.loads(item[1])

        return item

    async def len(self, queue=None):
        if queue is not None:
            return self.client.llen(queue)
        else:
            return self.client.llen('queue')

    async def set(self, key, value, ttl=None):
        if isinstance(value, dict):
            value = json.dumps(value)

        self.client.set(key, value, ttl)

    async def get(self, key):
        return self.client.get(key)

    async def exists(self, key):
        return self.client.exists(key)

    async def decr(self, key):
        await self.client.decr(key)

    async def publish(self, channel, message):
        await self.client.publish(channel, message)

