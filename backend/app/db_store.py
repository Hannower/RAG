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

PT_NUM_WORDS = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "três": 3,
    "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9,
    "dez": 10, "onze": 11, "doze": 12, "treze": 13, "quatorze": 14, "catorze": 14,
    "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19,
    "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60,
    "setenta": 70, "oitenta": 80, "noventa": 90, "cem": 100, "cento": 100,
    "duzentos": 200, "trezentos": 300, "quatrocentos": 400, "quinhentos": 500,
    "seiscentos": 600, "setecentos": 700, "oitocentos": 800, "novecentos": 900,
}

def extract_numbers_from_query(query: str) -> List[float]:
    """Extrai valores numéricos explícitos ou falados (ex: 'sete mil' -> 7000.0) da consulta."""
    q = query.lower()
    found_nums: List[float] = []

    # Detecta padrões falados como 'X mil' ou 'X milhões'
    mil_matches = list(re.finditer(r'\b([a-záéíóúãõâêîôûç]+|\d+)\s+mil(?:h[aã]o|h[oõ]es)?\b', q))
    matched_spans = []
    for m in mil_matches:
        mult = m.group(1)
        factor = 1000000 if 'milh' in m.group(0) else 1000
        val = None
        if mult.isdigit():
            val = float(mult) * factor
        elif mult in PT_NUM_WORDS:
            val = float(PT_NUM_WORDS[mult]) * factor
        if val is not None:
            found_nums.append(val)
            matched_spans.append(m.span())

    # Detecta dígitos numéricos explícitos (ex: 7000, 10.000, 46500.00)
    for num_match in re.finditer(r'\b\d+(?:[\.,]\d+)*\b', q):
        span = num_match.span()
        if any(s[0] <= span[0] and span[1] <= s[1] for s in matched_spans):
            continue
        clean = num_match.group(0).replace('.', '').replace(',', '.')
        try:
            val = float(clean)
            if val not in found_nums:
                found_nums.append(val)
        except ValueError:
            pass

    return found_nums

def classify_query_intent(query_text: str) -> Dict[str, Any]:
    """
    Classifica a intenção da consulta para aplicar roteamento e contextualização inteligente:
    - specific_invoice: menção a uma nota específica (ex: NF-001001)
    - is_aggregation: solicita cálculo agregado (soma, total, quantas notas, média)
    - is_comparison: solicita comparação ou filtro numérico (mais de, maior que, acima de)
    - is_collection: refere-se ao conjunto de notas (quais notas, todas as notas)
    - is_items_query: pergunta voltada a produtos/itens específicos
    - is_global_or_multi_doc: consulta que necessita de visibilidade de todas as notas fiscais
    """
    q = query_text.lower().strip()

    specific_invoice = None
    inv_match = re.search(r'\b(?:nf-?)?0*(100[1-9])\b', q)
    if inv_match:
        specific_invoice = f"NF-00{inv_match.group(1)}"
    elif re.search(r'\bnf-?\d+\b', q):
        specific_invoice = re.search(r'\bnf-?\d+\b', q).group(0).upper()

    is_aggregation = bool(re.search(
        r'\b(?:soma|somar|somat[oó]rio|total|totais|quantas?\s+notas?|quantidade\s+de\s+notas?|m[eé]dia|faturamento)\b',
        q
    ))

    is_comparison = bool(re.search(
        r'\b(?:mais\s+de|maior\s+que|maiores\s+que|acima\s+de|superior\s+a|menos\s+de|menor\s+que|menores\s+que|abaixo\s+de|inferior\s+a|mais\s+cara|mais\s+barata|maior\s+valor|menor\s+valor|ultrapassam|custam|possuem\s+mais|possuem\s+menos)\b',
        q
    ))

    is_collection = bool(re.search(
        r'\b(?:todas\s+(?:as\s+)?notas?|todas\s+as\s+nfs?|quais\s+(?:s[aã]o\s+as\s+)?notas?|quais\s+nfs?|listar\s+(?:as\s+)?notas?|quais\s+foram\s+emitidas|cada\s+nota|as\s+notas\s+fiscais)\b',
        q
    ))

    is_items_query = bool(re.search(
        r'\b(?:itens?|produtos?|servi[çc]os?|descri[çc][aã]o|comprado|comprados|adquirido|adquiridos)\b',
        q
    ))

    is_global_or_multi_doc = (is_aggregation or is_comparison or is_collection) and (specific_invoice is None)

    return {
        "specific_invoice": specific_invoice,
        "is_global_or_multi_doc": is_global_or_multi_doc,
        "is_aggregation": is_aggregation,
        "is_comparison": is_comparison,
        "is_collection": is_collection,
        "is_items_query": is_items_query,
        "extracted_numbers": extract_numbers_from_query(query_text)
    }

def calculate_lexical_boost(query_text: str, content: str, invoice_number: str = "", chunk_type: str = "") -> float:
    """
    Calcula um boost léxico híbrido considerando:
    1. Menção explícita à nota fiscal ou número
    2. Correspondência de palavras-chave da consulta
    3. Relevância monetária para perguntas de valor/soma vs observações sem valores
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

    # 2. Extração de palavras-chave significativas
    words = re.findall(r'\b[a-zA-Z0-9áéíóúãõâêîôûç]{3,}\b', q_lower)
    sig_keywords = [w for w in words if w not in STOPWORDS_PT]
    if sig_keywords:
        matches = 0
        for kw in sig_keywords:
            stem = kw[:-1] if kw.endswith('s') and len(kw) > 4 else kw
            if kw in c_lower or stem in c_lower:
                matches += 1
        if matches > 0:
            ratio = matches / len(sig_keywords)
            boost += min(0.12, 0.04 * matches + 0.02 * ratio)

    # 3. Boost contextual para consultas de valores e cálculos
    is_value_q = any(w in q_lower for w in ["valor", "soma", "reais", "total", "custam", "preço", "preco"])
    if is_value_q:
        if "valor total" in c_lower or "r$" in c_lower:
            boost += 0.06
        # Desencoraja chunks de observações sem números monetários a sobreporem dados financeiros
        if chunk_type == "notes_and_context" and "r$" not in c_lower:
            boost -= 0.06

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

    def get_header_chunks(self, base_id: str = "default") -> List[Dict[str, Any]]:
        """
        Retorna todos os chunks de cabeçalho estruturado (chunk_index == 0 ou chunk_type == 'header_metadata')
        da base informada. Esses chunks contêm os metadados vitais de cada nota: número, data,
        fornecedor, destinatário e o Valor Total Geral.
        """
        headers = []
        if self.use_supabase and self.client:
            try:
                res = self.client.table("rag_chunks").select("id, document_id, base_id, chunk_index, content, token_count, metadata").eq("base_id", base_id).execute()
                if res.data:
                    for row in res.data:
                        meta = row.get("metadata") or {}
                        if row.get("chunk_index") == 0 or meta.get("chunk_type") == "header_metadata":
                            headers.append({
                                "id": row.get("id"),
                                "chunk_id": row.get("id"),
                                "document_id": row.get("document_id"),
                                "chunk_index": row.get("chunk_index", 0),
                                "chunk_type": meta.get("chunk_type", "header_metadata"),
                                "content": row.get("content", ""),
                                "token_count": row.get("token_count", 0),
                                "metadata": meta,
                                "invoice_number": meta.get("invoice_number", "")
                            })
                    if headers:
                        headers.sort(key=lambda x: str(x.get("invoice_number", "")))
                        return headers
            except Exception as e:
                print(f"Aviso ao buscar header chunks no Supabase: {e}")

        # Fallback local
        data = self._load_local_data()
        for ch in data.get("chunks", []):
            if ch.get("base_id", "default") == base_id:
                if ch.get("chunk_index") == 0 or ch.get("chunk_type") == "header_metadata":
                    headers.append({
                        "id": ch.get("id"),
                        "chunk_id": ch.get("id"),
                        "document_id": ch.get("document_id"),
                        "chunk_index": ch.get("chunk_index", 0),
                        "chunk_type": ch.get("chunk_type", "header_metadata"),
                        "content": ch.get("content", ""),
                        "token_count": ch.get("token_count", 0),
                        "metadata": {"invoice_number": ch.get("invoice_number"), "chunk_type": ch.get("chunk_type")},
                        "invoice_number": ch.get("invoice_number", "")
                    })
        headers.sort(key=lambda x: str(x.get("invoice_number", "")))
        return headers

    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        base_id: str = "default",
        similarity_threshold: float = 0.58,
        query_text: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Executa a busca vetorial por similaridade de cosseno (Cosine Similarity) combinada
        com RAG Híbrido, desempate léxico inteligente e roteamento contextual para perguntas
        globais, de agregação (soma, total) e de comparação numérica.
        """
        intent = classify_query_intent(query_text)
        candidates_map: Dict[str, Dict[str, Any]] = {}

        # 1. Recuperação Vetorial Primária via Supabase (se conectado) ou Local
        if self.use_supabase and self.client:
            try:
                fetch_count = max(top_k * 4, 30)
                res = self.client.rpc("match_rag_chunks", {
                    "query_embedding": query_embedding,
                    "match_count": fetch_count,
                    "filter_base_id": base_id
                }).execute()

                if res.data:
                    for row in res.data:
                        cid = row.get("id")
                        content = row.get("content", "")
                        meta = row.get("metadata") or {}
                        inv_num = meta.get("invoice_number", "")
                        ctype = meta.get("chunk_type", "")
                        base_sim = float(row.get("similarity", 0.0))

                        # Aplica boost léxico e monetário
                        boost = calculate_lexical_boost(query_text, content, inv_num, ctype)
                        final_sim = round(min(0.99, max(0.0, base_sim + boost)), 4)

                        candidates_map[cid] = {
                            "id": cid,
                            "chunk_id": cid,
                            "document_id": row.get("document_id"),
                            "chunk_index": row.get("chunk_index"),
                            "chunk_type": ctype,
                            "invoice_number": inv_num,
                            "content": content,
                            "similarity": final_sim,
                            "token_count": row.get("token_count", 0),
                            "metadata": meta
                        }
            except Exception as e:
                print(f"Aviso no RPC do Supabase: {e}")

        # Se Supabase não retornou candidatos (ou fallback local), usa busca local
        if not candidates_map:
            data = self._load_local_data()
            chunks = [c for c in data.get("chunks", []) if c.get("base_id", "default") == base_id]
            for ch in chunks:
                ch_emb = ch.get("embedding", [])
                content = ch.get("content", "")
                if not ch_emb or len(ch_emb) != len(query_embedding):
                    continue
                cid = ch.get("id")
                inv_num = str(ch.get("invoice_number", ""))
                ctype = ch.get("chunk_type", "")
                base_sim = cosine_similarity(query_embedding, ch_emb)
                boost = calculate_lexical_boost(query_text, content, inv_num, ctype)
                final_sim = round(min(0.99, max(0.0, base_sim + boost)), 4)

                candidates_map[cid] = {
                    "id": cid,
                    "chunk_id": cid,
                    "document_id": ch.get("document_id"),
                    "chunk_index": ch.get("chunk_index"),
                    "chunk_type": ctype,
                    "invoice_number": inv_num,
                    "content": content,
                    "similarity": final_sim,
                    "token_count": ch.get("token_count", 0),
                    "metadata": {"invoice_number": inv_num, "chunk_type": ctype}
                }

        # 2. Tratamento Especial para Consultas Globais, Agregações e Comparações de Notas
        # Ex: "Qual a soma das notas fiscais?", "Quais notas possuem mais de 7 mil reais?"
        if intent["is_global_or_multi_doc"]:
            headers = self.get_header_chunks(base_id=base_id)
            for h in headers:
                hid = h["chunk_id"]
                if hid in candidates_map:
                    candidates_map[hid]["similarity"] = max(candidates_map[hid]["similarity"], 0.90)
                else:
                    candidates_map[hid] = {
                        "id": hid,
                        "chunk_id": hid,
                        "document_id": h.get("document_id"),
                        "chunk_index": h.get("chunk_index", 0),
                        "chunk_type": "header_metadata",
                        "invoice_number": h.get("invoice_number", ""),
                        "content": h.get("content", ""),
                        "similarity": 0.90,
                        "token_count": h.get("token_count", 0),
                        "metadata": h.get("metadata", {})
                    }

        # 3. Filtro pelo limiar de similaridade
        filtered_candidates = [
            c for c in candidates_map.values()
            if c["similarity"] >= similarity_threshold
        ]

        # 4. Ordenação por similaridade decrescente
        filtered_candidates.sort(key=lambda x: x["similarity"], reverse=True)

        # 5. Se for consulta global, garante que pelo menos todos os headers caibam no retorno
        effective_top_k = top_k
        if intent["is_global_or_multi_doc"]:
            header_count = sum(1 for c in filtered_candidates if c.get("chunk_type") == "header_metadata")
            effective_top_k = max(top_k, header_count)

        results = filtered_candidates[:effective_top_k]
        for rank, item in enumerate(results, start=1):
            item["rank"] = rank

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
