from typing import List
from fastembed import TextEmbedding

# Modelo BAAI/bge-small-en-v1.5: 384 dimensões
_model = None

def get_embedding_model():
    global _model
    if _model is None:
        _model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _model

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Gera embeddings reais usando FastEmbed.
    Retorna uma lista de vetores de floats com 384 dimensões.
    """
    model = get_embedding_model()
    embeddings = list(model.embed(texts))
    return [e.tolist() for e in embeddings]

def generate_single_embedding(text: str) -> List[float]:
    """
    Gera embedding para um texto único (como a pergunta do usuário).
    """
    return generate_embeddings([text])[0]
