from fastapi import APIRouter

from backend.app.api.routes import auth, chat, health, knowledge, orders, rag

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(orders.router)
api_router.include_router(chat.router)
api_router.include_router(knowledge.router)
api_router.include_router(rag.router)
