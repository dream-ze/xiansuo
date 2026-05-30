import logging
import time
import traceback
from collections import defaultdict

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes.ai import router as ai_router
from app.api.routes.accounts import router as accounts_router
from app.api.routes.auth import router as auth_router
from app.api.routes.collectors import router as collectors_router
from app.api.routes.comments import router as comments_router
from app.api.routes.collection_tasks import router as collection_tasks_router
from app.api.routes.content_pools import router as content_pools_router
from app.api.routes.crawl_tasks import router as crawl_tasks_router
from app.api.routes.crm import router as crm_router
from app.api.routes.daily_reports import router as daily_reports_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.drafts import router as drafts_router
from app.api.routes.files import router as files_router
from app.api.routes.keyword_groups import router as keyword_groups_router
from app.api.routes.leads import router as leads_router
from app.api.routes.login_sessions import router as login_sessions_router
from app.api.routes.model_configs import router as model_configs_router
from app.api.routes.monitor_sources import router as monitor_sources_router
from app.api.routes.notes import router as notes_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.pending_competitors import router as pending_competitors_router
from app.api.routes.publish import router as publish_router
from app.api.routes.scoring_rules import router as scoring_rules_router
from app.api.routes.tags import router as tags_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.posts import router as posts_router
from app.api.routes.xhs_analytics import router as xhs_analytics_router
from app.api.routes.xhs_auto_ops import router as xhs_auto_ops_router
from app.api.routes.xhs_monitoring import router as xhs_monitoring_router
from app.api.routes.video_studio import router as video_studio_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(application: FastAPI):
    from app.services.crawl_scheduler import start_scheduler, stop_scheduler
    if settings.scheduler_enabled:
        start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

logger = logging.getLogger(__name__)


_RATE_LIMIT_WINDOW = 60
_RATE_LIMIT_MAX_REQUESTS = 20
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    logger.info(
        "%s %s -> %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    auth_paths = ("/api/auth/login", "/api/auth/register")
    if request.url.path not in auth_paths:
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = _rate_limit_store[client_ip]
    window[:] = [t for t in window if now - t < _RATE_LIMIT_WINDOW]
    if len(window) >= _RATE_LIMIT_MAX_REQUESTS:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please try again later."},
        )
    window.append(now)
    return await call_next(request)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s\n%s", exc, traceback.format_exc())
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth_router)
app.include_router(accounts_router)
app.include_router(login_sessions_router)
app.include_router(keyword_groups_router)
app.include_router(notes_router)
app.include_router(publish_router)
app.include_router(tags_router)
app.include_router(ai_router)
app.include_router(posts_router)
app.include_router(comments_router)
app.include_router(collection_tasks_router)
app.include_router(leads_router)
app.include_router(dashboard_router)
app.include_router(daily_reports_router)
app.include_router(pending_competitors_router)
app.include_router(content_pools_router)
app.include_router(crawl_tasks_router)
app.include_router(crm_router)
app.include_router(monitor_sources_router)
app.include_router(collectors_router)
app.include_router(scoring_rules_router)
app.include_router(drafts_router)
app.include_router(files_router)
app.include_router(model_configs_router)
app.include_router(notifications_router)
app.include_router(tasks_router)
app.include_router(xhs_analytics_router)
app.include_router(xhs_auto_ops_router)
app.include_router(xhs_monitoring_router)
app.include_router(video_studio_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
