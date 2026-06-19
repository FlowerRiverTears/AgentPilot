from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.auth import seed_admin_user
from app.core.aspects import AspectMiddleware
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.models import Agent, AgentRun, Document, DocumentChunk, KnowledgeBase, RunStep, Tool, ToolCall, User
from app.repositories.memory import store


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_admin_user()
    await store.initialize()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI Agent creation, RAG, vector search and observability platform.",
        lifespan=lifespan,
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

    return app


app = create_app()
