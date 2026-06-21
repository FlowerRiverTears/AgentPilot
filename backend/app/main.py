from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.auth import seed_admin_user
from app.core.aspects import AspectMiddleware
from app.core.config import settings
from app.core.errors import create_error_response, ErrorCode, generic_error_handler
from app.db.base import Base
from app.db.session import engine
from app.models import Agent, AgentRun, Conversation, Document, DocumentChunk, EvalDataset, EvalResult, Feedback, KnowledgeBase, RagConfig, RunStep, Tool, ToolCall, User, Workflow, WorkflowRun
from app.repositories.memory import store

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure structured logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    settings.validate_security()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_admin_user()
    await get_store().initialize()
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

    app.add_exception_handler(Exception, generic_error_handler)
    app.add_exception_handler(RequestValidationError, lambda r, e: create_error_response(ErrorCode.VALIDATION, str(e), 422))

    app.include_router(api_router, prefix=settings.api_prefix)

    return app


app = create_app()
