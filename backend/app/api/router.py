from fastapi import APIRouter

from app.api.routes import agents, health, knowledge, mock, runs, settings, tools

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(knowledge.router, prefix="/knowledge-bases", tags=["knowledge"])
api_router.include_router(runs.router, prefix="/runs", tags=["runs"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])
api_router.include_router(mock.router, prefix="/mock", tags=["mock"])
