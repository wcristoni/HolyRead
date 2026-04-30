"""HolyRead V1 backend — Bíblia + estudo no original."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .config import ALLOWED_ORIGINS, ALLOWED_ORIGIN_REGEX
from .limiter import limiter
from .routes import analytics, bible, original

app = FastAPI(
    title="HolyRead API",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    max_age=600,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "interest-cohort=()"
    return response


app.include_router(bible.router)
app.include_router(original.router)
app.include_router(analytics.router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "HolyRead API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}
