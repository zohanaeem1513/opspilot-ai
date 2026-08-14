from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.ready import router as ready_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.include_router(health_router)
app.include_router(ready_router)
