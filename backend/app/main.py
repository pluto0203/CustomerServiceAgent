from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.endpoints.agent_input import router as agent_input_router
from app.api.v1.endpoints.skill_runs import router as skill_runs_router
from app.core.config import settings
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: warm-up DB connection pool
    yield
    # Shutdown: đóng engine pool gọn ghẽ
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description="Module phân tích hành vi khách hàng trong hệ thống MultiAgentAssistant.",
    version=settings.AGENT_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.include_router(agent_input_router, prefix="/api/v1")
app.include_router(skill_runs_router, prefix="/api/v1")


@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "agent": settings.AGENT_ID,
        "version": settings.AGENT_VERSION,
        "env": settings.APP_ENV,
    }
