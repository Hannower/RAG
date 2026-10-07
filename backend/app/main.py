import os
import uuid
import shutil
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.app.extractor import extract_text_and_tables_from_pdf
from backend.app.chunker import chunk_document, tokenize_text
from backend.app.embedder import generate_embeddings, generate_single_embedding
from backend.app.db_store import db_store
from backend.app.llm_client import build_augmented_prompt, call_llm

app = FastAPI(
    title="RAG + Hannower API",
    description="API do Pipeline Didático RAG",
    version="1.0.0"
)

# Configura CORS para permitir acesso do Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads")
INVOICES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "invoices")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(INVOICES_DIR, exist_ok=True)

class QueryRequest(BaseModel):
    question: str
    base_id: Optional[str] = "default"
    top_k: Optional[int] = 5

@app.get("/api/health")
def health():
    return {
        "status": "online",
        "supabase_connected": db_store.use_supabase,
        "embedding_model": "BAAI/bge-small-en-v1.5 (FastEmbed, dim=384)",
        "llm_model": "openrouter/auto"
    }

@app.get("/api/bases")
def get_bases():
    return db_store.get_bases()

@app.get("/api/documents")
def get_documents(base_id: str = "default"):
    return db_store.get_all_documents(base_id=base_id)

@app.post("/api/ingest/default-invoices")
def ingest_default_invoices(base_id: str = "default"):
    """
    Ingere os 4 PDFs fictícios de notas fiscais pré-gerados, retornando o trace didático completo.
    """
    results = []
    if not os.path.exists(INVOICES_DIR):
        raise HTTPException(status_code=404, detail="Diretório de notas fiscais não encontrado.")

    files = [f for f in os.listdir(INVOICES_DIR) if f.endswith(".pdf")]
    files.sort()

    for f in files:
        file_path = os.path.join(INVOICES_DIR, f)
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        trace = process_pdf_document(file_path, f, doc_id, base_id)
        results.append(trace)

    return {
        "message": f"{len(results)} documentos foram ingeridos com sucesso no banco!",
        "documents_processed": results
    }

@app.post("/api/ingest/upload")
async def upload_and_ingest(file: UploadFile = File(...), base_id: str = Form("default")):
    """
    Permite upload de novos arquivos PDF e realiza todo o pipeline RAG didático.
    """
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}_{file.filename}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    trace = process_pdf_document(file_path, file.filename, doc_id, base_id)
    return {
        "message": f"Documento '{file.filename}' processado com sucesso!",
        "document_processed": trace
    }

def process_pdf_document(file_path: str, filename: str, doc_id: str, base_id: str) -> Dict[str, Any]:
    """
    Executa passo a passo didático:
    1. Leitura e OCR
    2. Estruturação tabular
    3. Chunking com metadados
    4. Tokenização com tiktoken
    5. Geração de Embeddings com FastEmbed (384 dim)
    6. Persistência Vetorial no Supabase / Vector Store
    """
    # 1. OCR e Extração
    extraction_res = extract_text_and_tables_from_pdf(file_path)
    parsed = extraction_res["parsed_fields"]
    raw_text = extraction_res["raw_text"]

    # 2. Chunking & Tokenização
    chunks = chunk_document(doc_id, parsed["numero_nota"], parsed, raw_text)

    # 3. Geração de Embeddings reais com FastEmbed
    chunk_texts = [c["content"] for c in chunks]
    embeddings = generate_embeddings(chunk_texts)

    # 4. Persistência
    doc_info = {
        "id": doc_id,
        "filename": filename,
        "numero_nota": parsed["numero_nota"],
        "data_emissao": parsed["data_emissao"],
        "fornecedor": parsed["fornecedor"],
        "cnpj": parsed["cnpj"],
        "cliente": parsed["cliente"],
        "cliente_cnpj": parsed["cliente_cnpj"],
        "valor_total": parsed["valor_total"],
        "raw_text": raw_text,
        "parsed_fields": parsed
    }
    db_store.save_document_and_chunks(doc_info, chunks, embeddings, base_id=base_id)

    # Prepara objeto de observabilidade didática
    chunks_preview = []
    for c, emb in zip(chunks, embeddings):
        chunks_preview.append({
            "chunk_id": c["chunk_id"],
            "chunk_index": c["chunk_index"],
            "chunk_type": c.get("chunk_type"),
            "token_count": c["token_count"],
            "tokens_visual": c.get("tokens_visual", []),
            "content": c["content"],
            "embedding_preview": emb[:6], # Amostra didática das 384 dimensões
            "embedding_dimension": len(emb)
        })

    return {
        "doc_id": doc_id,
        "filename": filename,
        "used_ocr": extraction_res["used_ocr"],
        "parsed_fields": parsed,
        "total_chunks": len(chunks),
        "chunks": chunks_preview
    }

@app.post("/api/query")
def query_rag(req: QueryRequest):
    """
    Executa o Pipeline completo de Consulta RAG:
    1. Pergunta do usuário
    2. Tokenização da pergunta
    3. Embedding da pergunta via FastEmbed
    4. Retrieval vetorial (top_k=5)
    5. Regra anti-alucinação: se sem candidatos relevantes -> 'Sem dados disponiveis na base'
    6. Construção do prompt aumentado
    7. Invocação do LLM via OpenRouter
    8. Retorno detalhado para visualização na UI
    """
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="A pergunta não pode estar vazia.")

    # 1. Tokenização da Pergunta
    question_token_data = tokenize_text(question)

    # 2. Embedding da Pergunta
    question_embedding = generate_single_embedding(question)

    # 3. Retrieval no Banco Vetorial (top_k configurável, padrão 5)
    top_k = req.top_k or 5
    retrieved_chunks = db_store.search_similar(
        query_embedding=question_embedding,
        top_k=top_k,
        base_id=req.base_id or "default"
    )

    # 4. Verificação de Ausência de Dados (Regra Anti-Alucinação Estrita)
    # Exige que o candidato mais relevante tenha pelo menos 0.72 de similaridade semântica
    if not retrieved_chunks or retrieved_chunks[0]["similarity"] < 0.72:
        return {
            "question": question,
            "pipeline": {
                "tokenization": question_token_data,
                "embedding_preview": question_embedding[:6],
                "embedding_dimension": len(question_embedding),
                "top_k": top_k,
                "candidates_found": 0,
                "candidates": []
            },
            "augmented_prompt": None,
            "answer": "Sem dados disponiveis na base",
            "model_info": "openrouter/auto (Não acionado - Ausência de candidatos relevantes)"
        }

    # 5. Construção do Prompt Aumentado
    augmented_prompt = build_augmented_prompt(question, retrieved_chunks)

    # 6. Chamada ao LLM via OpenRouter
    llm_result = call_llm(augmented_prompt)

    return {
        "question": question,
        "pipeline": {
            "tokenization": question_token_data,
            "embedding_preview": question_embedding[:6],
            "embedding_dimension": len(question_embedding),
            "top_k": top_k,
            "candidates_found": len(retrieved_chunks),
            "candidates": retrieved_chunks
        },
        "augmented_prompt": augmented_prompt,
        "answer": llm_result.get("answer", "Sem dados disponiveis na base"),
        "model_info": llm_result.get("model_used", "openrouter/auto"),
        "token_usage": llm_result.get("usage", {})
    }
