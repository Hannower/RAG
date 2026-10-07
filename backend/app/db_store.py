import os
import json
import math
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_PUBLISHABLE_KEY")

class VectorStore:
    def __init__(self):
        self.client: Optional[Client] = None
        self.use_supabase = False
        self.fallback_file = os.path.join(os.path.dirname(__file__), "..", "..", "data", "local_vector_store.json")
        os.makedirs(os.path.dirname(self.fallback_file), exist_ok=True)
        self.init_connection()

    def init_connection(self):
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
                # Testa se a tabela rag_chunks está acessível no Supabase
                res = self.client.table("rag_chunks").select("id").limit(1).execute()
                self.use_supabase = True
                print("VectorStore: Conectado com sucesso ao Supabase com tabela rag_chunks ativa!")
            except Exception as e:
                self.use_supabase = False
                print(f"VectorStore: Supabase não possui tabelas criadas ({e}). Usando armazenamento estruturado local espelhado.")
        else:
            self.use_supabase = False

    def _load_local_data(self) -> Dict[str, Any]:
        if os.path.exists(self.fallback_file):
            try:
                with open(self.fallback_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"documents": {}, "chunks": [], "bases": [{"id": "default", "name": "Base Fiscal Padrão (Notas Fiscais)"}]}

    def _save_local_data(self, data: Dict[str, Any]):
        with open(self.fallback_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_bases(self) -> List[Dict[str, str]]:
        if self.use_supabase and self.client:
            try:
                res = self.client.table("rag_bases").select("*").execute()
                if res.data:
                    return res.data
            except Exception:
                pass
        data = self._load_local_data()
        return data.get("bases", [{"id": "default", "name": "Base Fiscal Padrão (Notas Fiscais)"}])

    def save_document_and_chunks(
        self,
        doc_info: Dict[str, Any],
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        base_id: str = "default"
    ):
        # 1. Se Supabase com tabelas estiver ativo, tenta persistir lá
        if self.use_supabase and self.client:
            try:
                # Upsert documento
                self.client.table("rag_documents").upsert({
                    "id": doc_info["id"],
                    "base_id": base_id,
                    "filename": doc_info["filename"],
                    "invoice_number": doc_info.get("numero_nota"),
                    "issue_date": doc_info.get("data_emissao"),
                    "supplier_name": doc_info.get("fornecedor"),
                    "supplier_cnpj": doc_info.get("cnpj"),
                    "customer_name": doc_info.get("cliente"),
                    "total_amount": doc_info.get("valor_total"),
                    "raw_text": doc_info.get("raw_text", ""),
                    "metadata": doc_info.get("parsed_fields", {})
                }).execute()

                # Upsert chunks com os vetores FastEmbed
                db_chunks = []
                for chunk, emb in zip(chunks, embeddings):
                    db_chunks.append({
                        "id": chunk["chunk_id"],
                        "document_id": doc_info["id"],
                        "base_id": base_id,
                        "chunk_index": chunk["chunk_index"],
                        "content": chunk["content"],
                        "token_count": chunk["token_count"],
                        "metadata": {
                            "invoice_number": chunk["invoice_number"],
                            "chunk_type": chunk.get("chunk_type")
                        },
                        "embedding": emb
                    })
                if db_chunks:
                    self.client.table("rag_chunks").upsert(db_chunks).execute()
                return
            except Exception as e:
                print(f"Erro ao salvar no Supabase, mantendo cópia local: {e}")

        # 2. Persistência local estruturada
        local_data = self._load_local_data()
        local_data["documents"][doc_info["id"]] = {
            "id": doc_info["id"],
            "base_id": base_id,
            "filename": doc_info["filename"],
            "invoice_number": doc_info.get("numero_nota"),
            "data_emissao": doc_info.get("data_emissao"),
            "fornecedor": doc_info.get("fornecedor"),
            "cnpj": doc_info.get("cnpj"),
            "cliente": doc_info.get("cliente"),
            "cliente_cnpj": doc_info.get("cliente_cnpj"),
            "valor_total": doc_info.get("valor_total"),
            "raw_text": doc_info.get("raw_text", ""),
            "parsed_fields": doc_info.get("parsed_fields", {})
        }

        # Remove chunks antigos do mesmo doc_id para atualizar
        local_data["chunks"] = [c for c in local_data["chunks"] if c.get("document_id") != doc_info["id"]]

        for chunk, emb in zip(chunks, embeddings):
            local_data["chunks"].append({
                "id": chunk["chunk_id"],
                "document_id": doc_info["id"],
                "base_id": base_id,
                "invoice_number": chunk["invoice_number"],
                "chunk_index": chunk["chunk_index"],
                "chunk_type": chunk.get("chunk_type"),
                "content": chunk["content"],
                "token_count": chunk["token_count"],
                "embedding": emb
            })
        self._save_local_data(local_data)

    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        base_id: str = "default",
        similarity_threshold: float = 0.68
    ) -> List[Dict[str, Any]]:
        """
        Executa a busca vetorial por similaridade de cosseno (Cosine Similarity).
        Filtra pelo limiar de relevância real para garantir o princípio anti-alucinação.
        """
        # 1. Tenta RPC no Supabase se ativo
        if self.use_supabase and self.client:
            try:
                res = self.client.rpc("match_rag_chunks", {
                    "query_embedding": query_embedding,
                    "match_count": top_k,
                    "filter_base_id": base_id
                }).execute()
                if res.data:
                    results = []
                    for rank, row in enumerate(res.data, start=1):
                        sim = float(row.get("similarity", 0.0))
                        if sim >= similarity_threshold:
                            results.append({
                                "rank": rank,
                                "document_id": row.get("document_id"),
                                "chunk_id": row.get("id"),
                                "chunk_index": row.get("chunk_index"),
                                "content": row.get("content"),
                                "similarity": round(sim, 4),
                                "metadata": row.get("metadata", {})
                            })
                    return results
            except Exception as e:
                print(f"Aviso no RPC do Supabase: {e}")

        # 2. Busca vetorial local com similaridade de cosseno matemática exata
        data = self._load_local_data()
        chunks = [c for c in data.get("chunks", []) if c.get("base_id", "default") == base_id]
        
        scored_chunks = []
        for ch in chunks:
            ch_emb = ch.get("embedding", [])
            if not ch_emb or len(ch_emb) != len(query_embedding):
                continue
            sim = cosine_similarity(query_embedding, ch_emb)
            scored_chunks.append({
                "chunk": ch,
                "similarity": sim
            })

        # Ordena descrescente pela similaridade
        scored_chunks.sort(key=lambda x: x["similarity"], reverse=True)

        results = []
        for rank, item in enumerate(scored_chunks[:top_k], start=1):
            sim = float(item["similarity"])
            if sim >= similarity_threshold:
                ch = item["chunk"]
                results.append({
                    "rank": rank,
                    "document_id": ch.get("document_id"),
                    "invoice_number": ch.get("invoice_number"),
                    "chunk_id": ch.get("id"),
                    "chunk_index": ch.get("chunk_index"),
                    "chunk_type": ch.get("chunk_type"),
                    "content": ch.get("content"),
                    "similarity": round(sim, 4),
                    "token_count": ch.get("token_count", 0)
                })

        return results

    def get_all_documents(self, base_id: str = "default") -> List[Dict[str, Any]]:
        data = self._load_local_data()
        docs = [d for d in data.get("documents", {}).values() if d.get("base_id", "default") == base_id]
        return docs

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

# Singleton
db_store = VectorStore()
