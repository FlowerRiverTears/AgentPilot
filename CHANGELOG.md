# Changelog

All notable changes to AgentPilot will be documented in this file.

## [3.0.0] - 2026-06-20

### Added
- **i18n**: Full Chinese/English language switching (vue-i18n)
- **Security**: JWT secret validation in production mode
- **Security**: API key encryption at rest (Fernet/AES-256)
- **Security**: Login rate limiting (5 attempts/minute)
- **Security**: Token blacklist for logout/revocation
- **Security**: RBAC with admin/user roles
- **Security**: SSRF protection for tool HTTP requests
- **Security**: Endpoint auth enhancement (runs, files, conversations)
- **Database**: Alembic migration support
- **Database**: Critical indexes on agent_runs, document_chunks, conversations, etc.
- **Database**: Pagination support on all list endpoints
- **Performance**: Parallel batch embedding for document upload
- **Performance**: Connection pool configuration (pool_size=20)
- **Performance**: N+1 query fix for multi-KB retrieval
- **Architecture**: Unified error response format
- **Architecture**: Shared repository base utilities
- **Architecture**: Centralized runtime configuration
- **Observability**: Enhanced health check with dependency verification
- **Frontend**: Language toggle button (中/EN) in both backend and portal

### Changed
- Default user role changed from "admin" to "user"
- Admin-only operations now require `get_current_admin` dependency
- All date formatting respects selected locale

## [2.0.0] - 2026-05-15

### Added
- Agent management: edit, publish, unpublish, duplicate, soft delete
- Run history: list, details, failed retry
- Tool system: HTTP tool creation, testing, runtime invocation, call logs
- Streaming output: SSE, Embedding, pgvector, PDF parsing, multi-turn context
- Multimodal retrieval: image extraction, multimodal Embedding, cross-modal retrieval, MinIO
- Basic auth: JWT + bcrypt, backend auth protection, portal anonymous access
- Portal experience: answer retry, error prompts, Mermaid chart rendering
- Conversation & agent: session management, context compression, multi-KB, import/export, feedback, template library

## [1.0.0] - 2026-04-01

### Added
- Knowledge base creation and document upload
- Document chunking and vector search
- Agent creation with model, KB, and tool binding
- Task execution with answer display and citation sources
- Standalone portal experience page
- Docker Compose one-click deployment
