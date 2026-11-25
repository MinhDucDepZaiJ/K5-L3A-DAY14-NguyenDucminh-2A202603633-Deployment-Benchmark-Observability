"""Track the agent's daily mock LLM costs in Redis."""
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException

from .config import settings
from .redis_client import r

# Integer nanodollars avoid accumulated floating-point rounding in Redis.
NANODOLLARS_PER_USD = 1_000_000_000
INPUT_TOKEN_COST = 150
OUTPUT_TOKEN_COST = 600


def _budget_key(day: date) -> str:
    return f"day14:cost:{day.isoformat()}"


def check_budget(day: date) -> None:
    spent = int(r.get(_budget_key(day)) or 0)
    if spent >= settings.daily_budget_usd * NANODOLLARS_PER_USD:
        raise HTTPException(status_code=402, detail="Daily budget exhausted")


def record_cost(day: date, input_tokens: int, output_tokens: int) -> float:
    cost = input_tokens * INPUT_TOKEN_COST + output_tokens * OUTPUT_TOKEN_COST
    key = _budget_key(day)
    expires = datetime.combine(day + timedelta(days=2), datetime.min.time(), timezone.utc)
    with r.pipeline() as transaction:
        transaction.incrby(key, cost)
        transaction.expireat(key, expires)
        transaction.execute()
    return cost / NANODOLLARS_PER_USD
