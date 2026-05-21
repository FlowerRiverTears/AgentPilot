from fastapi import APIRouter, HTTPException, UploadFile

from app.rag.pipeline import rag_pipeline
from app.repositories.memory import store
from app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    RetrieveRequest,
    RetrievedChunk,
)

router = APIRouter()


@router.get("", response_model=list[KnowledgeBaseRead])
async def list_knowledge_bases() -> list[KnowledgeBaseRead]:
    return store.list_knowledge_bases()


@router.post("", response_model=KnowledgeBaseRead, status_code=201)
async def create_knowledge_base(payload: KnowledgeBaseCreate) -> KnowledgeBaseRead:
    return store.create_knowledge_base(payload)


@router.delete("/{kb_id}", status_code=204)
async def delete_knowledge_base(kb_id: str) -> None:
    deleted = store.delete_knowledge_base(kb_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge base not found")


@router.post("/{kb_id}/documents", response_model=list[RetrievedChunk])
async def upload_document(kb_id: str, file: UploadFile) -> list[RetrievedChunk]:
    if kb_id not in store.knowledge_bases:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    raw = await file.read()
    text = raw.decode("utf-8", errors="ignore")
    chunks = rag_pipeline.build_chunks(file.filename or "uploaded-file", text)
    store.chunks[kb_id].extend(chunks)

    kb = store.knowledge_bases[kb_id]
    store.knowledge_bases[kb_id] = kb.model_copy(update={"document_count": kb.document_count + 1})
    return chunks


@router.post("/{kb_id}/retrieve-test", response_model=list[RetrievedChunk])
async def retrieve_test(kb_id: str, payload: RetrieveRequest) -> list[RetrievedChunk]:
    if kb_id not in store.knowledge_bases:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return rag_pipeline.retrieve(payload.query, store.chunks.get(kb_id, []), top_k=payload.top_k)
