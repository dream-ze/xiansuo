from fastapi import FastAPI

from app.api.routes.monitor_sources import router as monitor_sources_router

app = FastAPI(title="Loan Radar Backend")
app.include_router(monitor_sources_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
