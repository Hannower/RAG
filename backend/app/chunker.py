import tiktoken
from typing import List, Dict, Any

# Inicializa o tokenizer cl100k_base (padrão de modelos modernos de linguagem)
_encoder = tiktoken.get_encoding("cl100k_base")

def tokenize_text(text: str) -> Dict[str, Any]:
    """
    Realiza a tokenização explícita de um texto, permitindo observabilidade didática:
    - Retorna contagem de tokens
    - Retorna a lista de token IDs
    - Retorna os primeiros 50 tokens decodificados individualmente para exibição didática
    """
    tokens = _encoder.encode(text)
    decoded_pieces = []
    # Pega até 40 tokens para visualização didática sem sobrecarregar a UI
    for t in tokens[:40]:
        try:
            piece = _encoder.decode([t])
        except Exception:
            piece = f"[{t}]"
        decoded_pieces.append({"id": t, "piece": piece})

    return {
        "token_count": len(tokens),
        "token_ids_preview": tokens[:40],
        "tokens_visual": decoded_pieces
    }

def chunk_document(
    doc_id: str,
    invoice_number: str,
    parsed_fields: Dict[str, Any],
    raw_text: str,
    chunk_size: int = 150,
    chunk_overlap: int = 30
) -> List[Dict[str, Any]]:
    """
    Realiza o Chunking inteligente e didático do documento fiscal:
    
    Chunk 0: Resumo Estruturado dos Metadados da Nota Fiscal
    Chunk 1..N: Chunks dos Itens e produtos adquiridos
    Chunk N+1: Cláusulas adicionais, observações e totais
    
    Garante que cada chunk possua metadados claros (documento de origem, número da nota,
    posição do chunk e contagem de tokens).
    """
    chunks = []
    
    # Chunk 0: Cabeçalho e Dados Gerais
    header_content = (
        f"Nota Fiscal: {invoice_number}\n"
        f"Data de Emissão: {parsed_fields.get('data_emissao')}\n"
        f"Fornecedor / Emitente: {parsed_fields.get('fornecedor')} (CNPJ: {parsed_fields.get('cnpj')})\n"
        f"Cliente / Destinatário: {parsed_fields.get('cliente')} (CNPJ: {parsed_fields.get('cliente_cnpj')})\n"
        f"Valor Total Geral: R$ {parsed_fields.get('valor_total'):,.2f}"
    )
    tok_header = tokenize_text(header_content)
    chunks.append({
        "chunk_id": f"{doc_id}_chunk_0",
        "doc_id": doc_id,
        "invoice_number": invoice_number,
        "chunk_index": 0,
        "chunk_type": "header_metadata",
        "content": header_content,
        "token_count": tok_header["token_count"],
        "tokens_visual": tok_header["tokens_visual"]
    })

    # Chunks dos Itens: Agrupados para permitir recuperação contextual de produtos
    items = parsed_fields.get("itens", [])
    if items:
        # Agrupa itens em blocos de 2 produtos
        batch_size = 2
        for idx in range(0, len(items), batch_size):
            batch = items[idx:idx + batch_size]
            items_lines = []
            for item in batch:
                items_lines.append(
                    f"Item da Nota {invoice_number}: Produto/Serviço: '{item['descricao']}'. "
                    f"Quantidade: {item['quantidade']}. "
                    f"Valor Unitário: R$ {item['valor_unitario']:,.2f}. "
                    f"Valor Total do Item: R$ {item['valor_total']:,.2f}."
                )
            items_content = "\n".join(items_lines)
            chunk_idx = len(chunks)
            tok_item = tokenize_text(items_content)
            chunks.append({
                "chunk_id": f"{doc_id}_chunk_{chunk_idx}",
                "doc_id": doc_id,
                "invoice_number": invoice_number,
                "chunk_index": chunk_idx,
                "chunk_type": "invoice_items",
                "content": items_content,
                "token_count": tok_item["token_count"],
                "tokens_visual": tok_item["tokens_visual"]
            })

    # Chunk Final: Observações e Informações complementares
    # Procura seção de observações no texto bruto
    obs_content = ""
    if "Observações e Dados Adicionais" in raw_text:
        obs_content = raw_text.split("Observações e Dados Adicionais")[-1].strip()
    elif "Observacoes" in raw_text:
        obs_content = raw_text.split("Observacoes")[-1].strip()
    
    if obs_content:
        final_text = f"Nota Fiscal: {invoice_number} - Observações e Destinação: {obs_content}"
        chunk_idx = len(chunks)
        tok_final = tokenize_text(final_text)
        chunks.append({
            "chunk_id": f"{doc_id}_chunk_{chunk_idx}",
            "doc_id": doc_id,
            "invoice_number": invoice_number,
            "chunk_index": chunk_idx,
            "chunk_type": "notes_and_context",
            "content": final_text,
            "token_count": tok_final["token_count"],
            "tokens_visual": tok_final["tokens_visual"]
        })

    return chunks
