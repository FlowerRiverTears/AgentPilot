from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.core.deps import get_current_admin, get_current_user
from app.rag.document_loader import DocumentParseError, extract_upload, extract_upload_text
from app.rag.sample_documents import SAMPLE_DOCUMENTS
from app.repositories.memory import get_store
from app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    RetrieveRequest,
    RetrievedChunk,
)

router = APIRouter()

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB


@router.get("", response_model=list[KnowledgeBaseRead])
async def list_knowledge_bases(limit: int = 50, offset: int = 0, _user=Depends(get_current_user)) -> list[KnowledgeBaseRead]:
    return await get_store().list_knowledge_bases(limit=limit, offset=offset)


@router.post("", response_model=KnowledgeBaseRead, status_code=201)
async def create_knowledge_base(payload: KnowledgeBaseCreate, _user=Depends(get_current_admin)) -> KnowledgeBaseRead:
    return await get_store().create_knowledge_base(payload)


@router.delete("/{kb_id}", status_code=204)
async def delete_knowledge_base(kb_id: str, _user=Depends(get_current_admin)) -> None:
    deleted = await get_store().delete_knowledge_base(kb_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge base not found")


@router.post("/{kb_id}/documents", response_model=list[RetrievedChunk])
async def upload_document(kb_id: str, file: UploadFile, _user=Depends(get_current_admin)) -> list[RetrievedChunk]:
    if hasattr(file, 'size') and file.size and file.size > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")
    filename = file.filename or "uploaded-file"
    try:
        parsed = extract_upload(filename, file.content_type, raw)
    except DocumentParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not parsed.text.strip() and not parsed.images:
        raise HTTPException(status_code=400, detail="Document has no readable text or images")
    try:
        if parsed.images:
            chunks = await get_store().add_document_multimodal(kb_id, filename, parsed)
        else:
            chunks = await get_store().add_document(kb_id, filename, parsed.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not chunks:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return chunks


@router.get("/{kb_id}/documents", response_model=list[dict])
async def list_documents(kb_id: str, _user=Depends(get_current_user)) -> list[dict]:
    return await get_store().list_documents(kb_id)


@router.delete("/{kb_id}/documents/{doc_id}", status_code=204)
async def delete_document(kb_id: str, doc_id: str, _user=Depends(get_current_admin)) -> None:
    deleted = await get_store().delete_document(kb_id, doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")


@router.get("/sample-documents")
async def list_sample_documents(_user=Depends(get_current_user)) -> list[dict[str, str]]:
    return [
        {"id": document_id, "title": item["title"], "filename": item["filename"]}
        for document_id, item in SAMPLE_DOCUMENTS.items()
    ]


@router.post("/{kb_id}/sample-documents/{document_id}", response_model=list[RetrievedChunk])
async def import_sample_document(kb_id: str, document_id: str, _user=Depends(get_current_admin)) -> list[RetrievedChunk]:
    sample = SAMPLE_DOCUMENTS.get(document_id)
    if not sample:
        raise HTTPException(status_code=404, detail="Sample document not found")

    chunks = await get_store().add_document(kb_id, sample["filename"], sample["content"])
    if not chunks:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return chunks


@router.post("/{kb_id}/retrieve-test", response_model=list[RetrievedChunk])
async def retrieve_test(kb_id: str, payload: RetrieveRequest, _user=Depends(get_current_user)) -> list[RetrievedChunk]:
    return await get_store().retrieve_chunks(kb_id, payload.query, top_k=payload.top_k)


@router.post("/{kb_id}/retrieve-by-image", response_model=list[RetrievedChunk])
async def retrieve_by_image(kb_id: str, file: UploadFile, top_k: int = 5, _user=Depends(get_current_user)) -> list[RetrievedChunk]:
    """跨模态检索：上传图片，检索知识库中相关的文本块和图片块。"""
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Image file is empty")
    return await get_store().retrieve_by_image(kb_id, image_bytes, top_k=top_k)
