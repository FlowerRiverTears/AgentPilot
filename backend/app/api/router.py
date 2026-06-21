from fastapi import APIRouter

from app.api.routes import agents, audit, auth, conversations, eval, feedback, files, health, knowledge, mock, rag_tuning, runs, settings, tools, workflows, ws

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(knowledge.router, prefix="/knowledge-bases", tags=["knowledge"])
api_router.include_router(runs.router, prefix="/runs", tags=["runs"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(mock.router, prefix="/mock", tags=["mock"])
api_router.include_router(eval.router, prefix="/eval", tags=["eval"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(rag_tuning.router, prefix="/rag-tuning", tags=["rag-tuning"])
api_router.include_router(ws.router, tags=["ws"])
