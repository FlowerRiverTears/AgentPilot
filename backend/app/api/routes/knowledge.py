from fastapi import APIRouter, HTTPException, UploadFile

from app.rag.document_loader import DocumentParseError, extract_upload_text
from app.rag.sample_documents import SAMPLE_DOCUMENTS
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
    return await store.list_knowledge_bases()


@router.post("", response_model=KnowledgeBaseRead, status_code=201)
async def create_knowledge_base(payload: KnowledgeBaseCreate) -> KnowledgeBaseRead:
    return await store.create_knowledge_base(payload)


@router.delete("/{kb_id}", status_code=204)
async def delete_knowledge_base(kb_id: str) -> None:
    deleted = await store.delete_knowledge_base(kb_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge base not found")


@router.post("/{kb_id}/documents", response_model=list[RetrievedChunk])
async def upload_document(kb_id: str, file: UploadFile) -> list[RetrievedChunk]:
    raw = await file.read()
    filename = file.filename or "uploaded-file"
    try:
        text = extract_upload_text(filename, file.content_type, raw)
    except DocumentParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not text.strip():
        raise HTTPException(status_code=400, detail="Document has no readable text")
    try:
        chunks = await store.add_document(kb_id, filename, text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not chunks:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return chunks


@router.get("/sample-documents")
async def list_sample_documents() -> list[dict[str, str]]:
    return [
        {"id": document_id, "title": item["title"], "filename": item["filename"]}
        for document_id, item in SAMPLE_DOCUMENTS.items()
    ]


@router.post("/{kb_id}/sample-documents/{document_id}", response_model=list[RetrievedChunk])
async def import_sample_document(kb_id: str, document_id: str) -> list[RetrievedChunk]:
    sample = SAMPLE_DOCUMENTS.get(document_id)
    if not sample:
        raise HTTPException(status_code=404, detail="Sample document not found")

    chunks = await store.add_document(kb_id, sample["filename"], sample["content"])
    if not chunks:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return chunks


@router.post("/{kb_id}/retrieve-test", response_model=list[RetrievedChunk])
async def retrieve_test(kb_id: str, payload: RetrieveRequest) -> list[RetrievedChunk]:
    return await store.retrieve_chunks(kb_id, payload.query, top_k=payload.top_k)
