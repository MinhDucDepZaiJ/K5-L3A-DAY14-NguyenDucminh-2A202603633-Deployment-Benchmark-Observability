"""An atomic per-key sliding window shared by all workers."""
from hashlib import sha256
from uuid import uuid4

from fastapi import HTTPException

from .config import settings
from .redis_client import r

# Redis supplies a common clock for every replica. One script keeps counting
# and inserting atomic even when several workers receive requests together.
_sliding_window = r.register_script("""
local clock = redis.call('TIME')
local now = tonumber(clock[1]) * 1000 + math.floor(tonumber(clock[2]) / 1000)
local limit = tonumber(ARGV[1])
if limit <= 0 then return 60 end
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - 60000)
if redis.call('ZCARD', KEYS[1]) >= limit then
    local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    return math.max(1, math.ceil((60000 - (now - tonumber(oldest[2]))) / 1000))
end
redis.call('ZADD', KEYS[1], now, ARGV[2])
redis.call('PEXPIRE', KEYS[1], 60000)
return 0
""")


def check_rate_limit(key: str) -> None:
    digest = sha256(key.encode()).hexdigest()
    retry_after = _sliding_window(
        keys=[f"day14:rate:{digest}"],
        args=[settings.rate_limit_per_minute, uuid4().hex],
    )
    if retry_after:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
