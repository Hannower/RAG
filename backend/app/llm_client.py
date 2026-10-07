import os
import requests
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = "openrouter/auto"

SYSTEM_INSTRUCTION = """Você é o Assistente Didático RAG + Hannower, especializado em responder perguntas estritamente com base nos documentos recuperados do banco vetorial.

DIRETRIZES FUNDAMENTAIS:
1. Responda exclusivamente com base no CONTEXTO RECUPERADO fornecido abaixo.
2. Nunca invente dados, nomes, datas, itens ou valores.
3. Se o contexto não contiver a informação necessária para responder à pergunta, responda exatamente: "Sem dados disponiveis na base".
4. Seja didático, objetivo e claro em português. Cite de forma explicativa os números das notas fiscais e valores relevantes quando responder.
"""

def build_augmented_prompt(question: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
    """
    Constrói o prompt aumentado combinando:
    1. Instruções
    2. Contexto Recuperado do Vector Store
    3. Pergunta do Usuário
    """
    context_blocks = []
    for idx, c in enumerate(retrieved_chunks, start=1):
        context_blocks.append(
            f"--- [Candidato #{idx} | Nota: {c.get('invoice_number', 'N/A')} | Score: {c.get('similarity', 0.0)}] ---\n"
            f"{c.get('content', '')}"
        )
    
    context_str = "\n\n".join(context_blocks)
    prompt = (
        f"### CONTEXTO RECUPERADO (TOP CANDIDATOS DO RETRIEVAL):\n\n"
        f"{context_str}\n\n"
        f"### PERGUNTA DO USUÁRIO:\n"
        f"{question}\n\n"
        f"### RESPOSTA FINAL (Baseada exclusivamente no contexto acima):"
    )
    return prompt

def call_llm(augmented_prompt: str) -> Dict[str, Any]:
    """
    Comunica com o OpenRouter usando o modelo configurado em rag.txt (openrouter/auto).
    As credenciais são mantidas estritamente no backend.
    """
    if not OPENROUTER_API_KEY:
        return {
            "error": "Chave OPENROUTER_API_KEY não configurada no .env",
            "answer": "Erro de configuração: Chave OpenRouter não encontrada."
        }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://rag-teophilo.local",
        "X-Title": "RAG Didatico Teophilo"
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": augmented_prompt}
        ],
        "temperature": 0.1, # Temperatura baixa para evitar alucinação
        "max_tokens": 800
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            choice = data.get("choices", [{}])[0]
            answer = choice.get("message", {}).get("content", "").strip()
            return {
                "answer": answer,
                "model_used": data.get("model", OPENROUTER_MODEL),
                "usage": data.get("usage", {})
            }
        else:
            return {
                "error": f"Erro OpenRouter HTTP {response.status_code}: {response.text}",
                "answer": f"Falha na comunicação com o LLM (Status {response.status_code})"
            }
    except Exception as e:
        return {
            "error": str(e),
            "answer": f"Exceção ao chamar LLM: {str(e)}"
        }
