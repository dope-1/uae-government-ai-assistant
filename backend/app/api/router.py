from fastapi import APIRouter

from app.api.v1.agent import router as agent_router
from app.api.v1.chat import router as chat_router
from app.api.v1.health import router as health_router
from app.api.v1.ops import router as ops_router
from app.api.v1.search import router as search_router
from app.api.v1.services import router as services_router
from app.api.v1.sources import router as sources_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(chat_router)
api_router.include_router(search_router)
api_router.include_router(services_router)
api_router.include_router(sources_router)
api_router.include_router(agent_router)
api_router.include_router(ops_router)
