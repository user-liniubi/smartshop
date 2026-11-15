from fastapi import APIRouter

from backend.app.api.routes import (
    after_sales,
    after_sales_agent,
    agent,
    auth,
    chat,
    health,
    knowledge,
    orders,
    rag,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(orders.router)
api_router.include_router(chat.router)
api_router.include_router(after_sales.router)
api_router.include_router(after_sales_agent.router)
api_router.include_router(knowledge.router)
api_router.include_router(rag.router)
api_router.include_router(agent.router)
