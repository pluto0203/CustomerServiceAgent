from fastapi import FastAPI

from app.api.v1.endpoints.agent_input import router as agent_input_router

app = FastAPI(
    title="Customer Behavior Agent API",
    description="Module phân tích hành vi khách hàng trong hệ thống MultiAgentAssistant.",
    version="1.0.0",
)

app.include_router(agent_input_router, prefix="/api/v1")


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    return {"status": "ok"}
