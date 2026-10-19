import os
import json
import math
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(_ROOT_DIR / ".env")
load_dotenv(_ROOT_DIR / "env")
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_PUBLISHABLE_KEY")

STOPWORDS_PT = {
    "a", "ao", "aos", "as", "ate", "com", "como", "da", "das", "de", "do", "dos",
    "e", "em", "entre", "era", "essa", "essas", "esse", "esses", "esta", "estas",
    "este", "estes", "eu", "foi", "foram", "ha", "isso", "isto", "ja", "lhe",
    "me", "mesmo", "meu", "meus", "minha", "minhas", "muito", "na", "nas", "nao",
    "no", "nos", "nossa", "nossas", "nosso", "nossos", "num", "numa", "o", "os",
    "ou", "para", "pela", "pelas", "pelo", "pelos", "por", "qual", "quais", "quando",
    "quanto", "quantos", "que", "quem", "se", "sem", "ser", "seu", "seus", "so",
    "sua", "suas", "tambem", "te", "tem", "temos", "tenho", "ter", "teu", "teus",
    "tu", "tua", "tuas", "um", "uma", "umas", "uns", "voce", "voces", "possuem", "possui"
}

def calculate_lexical_boost(query_text: str, content: str, invoice_number: str = "") -> float:
    """
    Calcula um boost léxico híbrido (BM25 simplificado) combinando:
    1. Menção explícita à nota fiscal ou número
    2. Correspondência exata ou de radical das palavras-chave da consulta no chunk
    """
    if not query_text or not content:
        return 0.0

    q_lower = query_text.lower()
    c_lower = content.lower()
    boost = 0.0

    # 1. Menção ao número da nota fiscal
    if invoice_number:
        clean_inv = str(invoice_number).lower()
        clean_num = clean_inv.replace("nf-", "").replace("00", "")
        if clean_inv in q_lower or (len(clean_num) >= 3 and clean_num in q_lower):
            boost += 0.12

    # 2. Extração de palavras-chave da consulta
    words = re.findall(r'\b[a-zA-Z0-9áéíóúãõâêîôûç]{3,}\b', q_lower)
    sig_keywords = [w for w in words if w not in STOPWORDS_PT]
    if not sig_keywords:
        return boost

    matches = 0
    for kw in sig_keywords:
        stem = kw[:-1] if kw.endswith('s') and len(kw) > 4 else kw
        if kw in c_lower or stem in c_lower:
            matches += 1

    if matches > 0:
        ratio = matches / len(sig_keywords)
        # Boost progressivo com teto de +0.18
        boost += min(0.18, 0.08 * matches + 0.04 * ratio)

    return boost

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
        
        # Remove documento anterior com mesmo doc_id, filename ou numero_nota
        filename = doc_info.get("filename")
        invoice_number = doc_info.get("numero_nota")
        
        local_data["documents"] = {
            k: v for k, v in local_data["documents"].items()
            if k != doc_info["id"] 
            and v.get("filename") != filename 
            and (not invoice_number or v.get("invoice_number") != invoice_number)
        }
        
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

        # Remove chunks antigos do mesmo documento/nota para evitar duplicatas
        local_data["chunks"] = [
            c for c in local_data["chunks"] 
            if c.get("document_id") != doc_info["id"]
            and (not invoice_number or c.get("invoice_number") != invoice_number)
        ]

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
        similarity_threshold: float = 0.58,
        query_text: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Executa a busca vetorial por similaridade de cosseno (Cosine Similarity).
        Inclui desempate léxico inteligente (Hybrid RAG) caso o usuário mencione explicitamente
        o número da nota ou fornecedor, e garante que chunks duplicados não ocupem o top_k.
        """
        # 1. Tenta RPC no Supabase se ativo
        if self.use_supabase and self.client:
            try:
                res = self.client.rpc("match_rag_chunks", {
                    "query_embedding": query_embedding,
                    "match_count": top_k * 2,
                    "filter_base_id": base_id
                }).execute()
                if res.data:
                    scored_candidates = []
                    seen_contents = set()
                    q_lower = query_text.lower()
                    
                    for row in res.data:
                        content = row.get("content", "")
                        if content in seen_contents:
                            continue
                        seen_contents.add(content)
                        
                        sim = float(row.get("similarity", 0.0))
                        meta = row.get("metadata", {}) or {}
                        inv_num = meta.get("invoice_number", "")
                        
                        # Boost lexico leve se a pergunta citar diretamente o numero da nota
                        if inv_num and (inv_num.lower() in q_lower or inv_num.replace("nf-", "").lower() in q_lower):
                            sim += 0.10

                        if sim >= similarity_threshold:
                            scored_candidates.append({
                                "document_id": row.get("document_id"),
                                "chunk_id": row.get("id"),
                                "chunk_index": row.get("chunk_index"),
                                "content": content,
                                "similarity": round(sim, 4),
                                "metadata": meta,
                                "invoice_number": inv_num
                            })
                    
                    scored_candidates.sort(key=lambda x: x["similarity"], reverse=True)
                    for rank, item in enumerate(scored_candidates[:top_k], start=1):
                        item["rank"] = rank
                    return scored_candidates[:top_k]
            except Exception as e:
                print(f"Aviso no RPC do Supabase: {e}")

        # 2. Busca vetorial local com similaridade de cosseno e desempate híbrido
        data = self._load_local_data()
        chunks = [c for c in data.get("chunks", []) if c.get("base_id", "default") == base_id]
        
        q_lower = query_text.lower() if query_text else ""
        scored_chunks = []
        seen_contents = set()
        
        for ch in chunks:
            ch_emb = ch.get("embedding", [])
            content = ch.get("content", "")
            if not ch_emb or len(ch_emb) != len(query_embedding):
                continue
            if content in seen_contents:
                continue
            seen_contents.add(content)
            
            sim = cosine_similarity(query_embedding, ch_emb)
            
            # Boost hibrido caso a pergunta mencione especificamente a nota ou fornecedor
            inv_num = str(ch.get("invoice_number", ""))
            if inv_num and q_lower:
                clean_inv = inv_num.lower()
                clean_num = clean_inv.replace("nf-", "").replace("00", "")
                if clean_inv in q_lower or (len(clean_num) >= 3 and clean_num in q_lower):
                    sim += 0.12

            if sim >= similarity_threshold:
                scored_chunks.append({
                    "chunk": ch,
                    "similarity": sim
                })

        # Ordena descrescente pela similaridade
        scored_chunks.sort(key=lambda x: x["similarity"], reverse=True)

        results = []
        for rank, item in enumerate(scored_chunks[:top_k], start=1):
            ch = item["chunk"]
            results.append({
                "id": ch.get("id"),
                "chunk_id": ch.get("id"),
                "rank": rank,
                "document_id": ch.get("document_id"),
                "invoice_number": ch.get("invoice_number"),
                "chunk_index": ch.get("chunk_index"),
                "chunk_type": ch.get("chunk_type"),
                "content": ch.get("content"),
                "similarity": round(float(item["similarity"]), 4),
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
