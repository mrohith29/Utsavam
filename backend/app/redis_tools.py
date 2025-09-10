# backend/app/redis_tools.py
import os
import logging

# Use the modern redis-py asyncio client instead of the legacy aioredis package.
# This avoids compatibility issues and is actively maintained.
try:
    import redis.asyncio as redis_client
except Exception as e:
    logging.error("Failed to import redis.asyncio: %s", e)
    raise

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# create a redis client suitable for asyncio; decode_responses via encoding + decode_responses
redis = redis_client.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)

# Lua script for atomic decrement-if-enough
DECR_IF_ENOUGH = """
local key = KEYS[1]
local need = tonumber(ARGV[1])
local val = tonumber(redis.call("GET", key) or "-1")
if val == -1 then
  return -1
end
if val < need then
  return 0
end
redis.call("DECRBY", key, need)
return 1
"""

async def try_acquire_tokens(event_id: int, tokens: int = 1) -> bool | None:
    """
    Atomically attempt to consume `tokens` for event.
    - Returns True on success
    - Returns False on insufficient tokens
    - Returns None if the key is missing or Redis errored (caller may fall back to DB)
    """
    key = f"event:{event_id}:tokens"
    try:
        # redis.eval returns Python int when decode_responses=True
        res = await redis.eval(DECR_IF_ENOUGH, 1, key, str(tokens))
        # script returns 1 on success, 0 insufficient, -1 missing
        ival = int(res)
        if ival == 1:
            return True
        if ival == 0:
            return False
        # -1 means key missing; let caller decide via DB
        return None
    except Exception as exc:
        # Log for debugging and return False (fail-open versus fail-closed is a design choice).
        logging.exception("Redis error in try_acquire_tokens: %s", exc)
        return None

async def try_refund_tokens(event_id: int, tokens: int = 1) -> None:
    """
    Add tokens back to the bucket (best-effort).
    """
    key = f"event:{event_id}:tokens"
    try:
        await redis.incrby(key, int(tokens))
    except Exception as exc:
        logging.exception("Redis error in try_refund_tokens: %s", exc)
        # best-effort; swallow the exception

async def init_tokens_for_event(event_id: int, count: int) -> None:
    """
    Initialize the token key for an event to `count`. Overwrites existing value.
    """
    key = f"event:{event_id}:tokens"
    try:
        # ensure integer stored as string (redis-py handles this)
        await redis.set(key, int(count))
    except Exception as exc:
        logging.exception("Redis error in init_tokens_for_event: %s", exc)
        # best-effort; swallow

async def delete_tokens_for_event(event_id: int) -> None:
    """
    Delete the token key for an event (best-effort cleanup when deleting events).
    """
    key = f"event:{event_id}:tokens"
    try:
        await redis.delete(key)
    except Exception as exc:
        logging.exception("Redis error in delete_tokens_for_event: %s", exc)
        # best-effort; swallow