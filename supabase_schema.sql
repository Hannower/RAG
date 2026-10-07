-- Habilita a extensão PGVECTOR
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabela para armazenar as bases de dados / coleções didáticas
CREATE TABLE IF NOT EXISTS rag_bases (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Inserir base padrão
INSERT INTO rag_bases (id, name, description)
VALUES ('default', 'Base Fiscal - Notas Fiscais', 'Base de dados padrão contendo notas fiscais de teste para demonstração RAG')
ON CONFLICT (id) DO NOTHING;

-- Tabela de Documentos Ingeridos
CREATE TABLE IF NOT EXISTS rag_documents (
    id TEXT PRIMARY KEY,
    base_id TEXT REFERENCES rag_bases(id) ON DELETE CASCADE DEFAULT 'default',
    filename TEXT NOT NULL,
    invoice_number TEXT,
    issue_date TEXT,
    supplier_name TEXT,
    supplier_cnpj TEXT,
    customer_name TEXT,
    total_amount NUMERIC(12, 2),
    raw_text TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Tabela de Itens/Produtos das Notas Fiscais (Estrutura Tabular Didática)
CREATE TABLE IF NOT EXISTS rag_invoice_items (
    id BIGSERIAL PRIMARY KEY,
    document_id TEXT REFERENCES rag_documents(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    quantity NUMERIC(10, 2),
    unit_price NUMERIC(12, 2),
    total_price NUMERIC(12, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Tabela de Chunks com Vetores FastEmbed (384 dimensões - BAAI/bge-small-en-v1.5)
CREATE TABLE IF NOT EXISTS rag_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT REFERENCES rag_documents(id) ON DELETE CASCADE,
    base_id TEXT DEFAULT 'default',
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    token_count INT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding vector(384),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Índice IVFFlat ou HNSW para busca rápida por similaridade de cosseno
CREATE INDEX IF NOT EXISTS rag_chunks_embedding_cosine_idx 
ON rag_chunks USING hnsw (embedding vector_cosine_ops);

-- Função RPC para busca vetorial com top_k e filtro por base
CREATE OR REPLACE FUNCTION match_rag_chunks(
    query_embedding vector(384),
    match_count int DEFAULT 5,
    filter_base_id text DEFAULT 'default'
)
RETURNS TABLE (
    id text,
    document_id text,
    base_id text,
    chunk_index int,
    content text,
    token_count int,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.document_id,
        c.base_id,
        c.chunk_index,
        c.content,
        c.token_count,
        c.metadata,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM rag_chunks c
    WHERE (filter_base_id IS NULL OR c.base_id = filter_base_id)
      AND c.embedding IS NOT NULL
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
