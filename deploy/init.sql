CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS agentpilot_bootstrap (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO agentpilot_bootstrap (name)
VALUES ('AgentPilot database initialized')
ON CONFLICT DO NOTHING;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'document_chunks' AND column_name = 'content_type'
    ) THEN
        ALTER TABLE document_chunks ADD COLUMN content_type VARCHAR(20) NOT NULL DEFAULT 'text';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'document_chunks' AND column_name = 'image_url'
    ) THEN
        ALTER TABLE document_chunks ADD COLUMN image_url VARCHAR(500) NOT NULL DEFAULT '';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'document_chunks' AND column_name = 'source_uri'
    ) THEN
        ALTER TABLE document_chunks ADD COLUMN source_uri VARCHAR(500) NOT NULL DEFAULT '';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'document_chunks' AND column_name = 'section_path'
    ) THEN
        ALTER TABLE document_chunks ADD COLUMN section_path VARCHAR(500) NOT NULL DEFAULT '';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'document_chunks' AND column_name = 'page_number'
    ) THEN
        ALTER TABLE document_chunks ADD COLUMN page_number INTEGER;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'document_chunks' AND column_name = 'token_count'
    ) THEN
        ALTER TABLE document_chunks ADD COLUMN token_count INTEGER NOT NULL DEFAULT 0;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'document_chunks' AND column_name = 'chunk_metadata'
    ) THEN
        ALTER TABLE document_chunks ADD COLUMN chunk_metadata JSON NOT NULL DEFAULT '{}';
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding ON document_chunks
USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_document_chunks_content_type ON document_chunks (content_type);
CREATE INDEX IF NOT EXISTS idx_document_chunks_source_uri ON document_chunks (source_uri);
