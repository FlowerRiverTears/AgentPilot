from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.aspects import AspectMiddleware
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.models import Agent, AgentRun, Document, DocumentChunk, KnowledgeBase, RunStep, Tool
from app.llm.gateway import llm_gateway
from app.repositories.memory import store


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI Agent creation, RAG, vector search and observability platform.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AspectMiddleware)

    app.include_router(api_router, prefix=settings.api_prefix)

    @app.on_event("startup")
    async def startup() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await store.initialize()
        await llm_gateway.ensure_defaults()

    return app


app = create_app()
