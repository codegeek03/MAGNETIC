-- scripts/init_db.sql
-- Executed on first Postgres startup via docker-entrypoint-initdb.d
-- Enables the pgvector extension for semantic search / RAG.

CREATE EXTENSION IF NOT EXISTS vector;

-- Table for storing embedded document chunks (regulatory text, material data)
CREATE TABLE IF NOT EXISTS knowledge_embeddings (
    id            SERIAL PRIMARY KEY,
    source        VARCHAR(64) NOT NULL,     -- e.g. 'eurlex', 'openfoodfacts', 'pubmed'
    document_id   VARCHAR(256),              -- external document identifier
    chunk_text    TEXT NOT NULL,
    embedding     vector(768),               -- text-embedding-004 produces 768-dim vectors
    metadata      JSONB DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding
    ON knowledge_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Table for ambient agent alert events
CREATE TABLE IF NOT EXISTS alert_events (
    id            SERIAL PRIMARY KEY,
    event_type    VARCHAR(64) NOT NULL,     -- 'regulatory_change', 'new_material'
    summary       TEXT NOT NULL,
    details       JSONB DEFAULT '{}',
    acknowledged  BOOLEAN DEFAULT FALSE,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Table for analysis history (for the /api/v1/history endpoint)
CREATE TABLE IF NOT EXISTS analysis_history (
    id            SERIAL PRIMARY KEY,
    session_id    VARCHAR(128) UNIQUE NOT NULL,
    product_name  VARCHAR(256) NOT NULL,
    input_data    JSONB NOT NULL,
    result        JSONB,
    status        VARCHAR(32) DEFAULT 'processing',
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    completed_at  TIMESTAMPTZ
);
