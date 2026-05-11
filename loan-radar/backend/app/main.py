from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.comments import router as comments_router
from app.api.routes.content_pools import router as content_pools_router
from app.api.routes.crawl_tasks import router as crawl_tasks_router
from app.api.routes.daily_reports import router as daily_reports_router
from app.api.routes.leads import router as leads_router
from app.api.routes.monitor_sources import router as monitor_sources_router
from app.api.routes.pending_competitors import router as pending_competitors_router
from app.api.routes.posts import router as posts_router

app = FastAPI(title="Loan Radar Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(posts_router)
app.include_router(comments_router)
app.include_router(leads_router)
app.include_router(daily_reports_router)
app.include_router(pending_competitors_router)
app.include_router(content_pools_router)
app.include_router(crawl_tasks_router)
app.include_router(monitor_sources_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
