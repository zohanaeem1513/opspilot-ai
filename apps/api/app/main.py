from fastapi import FastAPI

from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.api.routes.me import router as me_router
from app.api.routes.ready import router as ready_router
from app.api.routes.workspaces import router as workspaces_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.include_router(health_router)
app.include_router(ready_router)
app.include_router(me_router)
app.include_router(workspaces_router)
app.include_router(documents_router)
