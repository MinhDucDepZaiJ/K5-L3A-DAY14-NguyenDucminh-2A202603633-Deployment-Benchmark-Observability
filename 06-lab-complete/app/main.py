"""FastAPI service for the Day 14 production agent."""
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from time import perf_counter

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from redis import RedisError

from utils.mock_llm import ask as llm_ask

from .auth import verify_api_key
from .cost_guard import check_budget, record_cost
from .rate_limiter import check_rate_limit
from .redis_client import r, redis_healthy

logger = logging.getLogger("day14.agent")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)
logger.propagate = False


def log_event(event: str, **fields) -> None:
    logger.info(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "lvl": "INFO",
        "event": event,
        **fields,
    }))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    log_event("startup")
    try:
        yield
    finally:
        r.close()
        log_event("shutdown")


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


@app.middleware("http")
async def log_request(request: Request, call_next):
    started = perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        log_event(
            "request",
            method=request.method,
            path=request.url.path,
            status=status,
            ms=round((perf_counter() - started) * 1000, 2),
        )


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    if not redis_healthy():
        raise HTTPException(status_code=503, detail="Redis unavailable")
    return {"ready": True}


@app.post("/ask")
def ask(body: AskRequest, key: str = Depends(verify_api_key)):
    day = datetime.now(timezone.utc).date()
    try:
        check_rate_limit(key)
        check_budget(day)
        answer = llm_ask(body.question)
        record_cost(day, len(body.question.split()) * 2, len(answer.split()) * 2)
    except RedisError as error:
        raise HTTPException(status_code=503, detail="Redis unavailable") from error
    return {"question": body.question, "answer": answer}
