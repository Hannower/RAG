from backend.app.db_store import classify_query_intent, extract_numbers_from_query, db_store
from backend.app.main import query_rag, QueryRequest
from backend.app.embedder import generate_single_embedding

def test_extract_numbers_from_query():
    assert 7000.0 in extract_numbers_from_query("Quais notas possuem mais de sete mil reais?")
    assert 10000.0 in extract_numbers_from_query("Notas com valor acima de 10.000")
    assert 5000.0 in extract_numbers_from_query("Notas acima de cinco mil reais")
    assert 20000.0 in extract_numbers_from_query("Valores superiores a vinte mil")
    assert len(extract_numbers_from_query("Qual a soma das notas fiscais?")) == 0

def test_classify_query_intent():
    q_soma = classify_query_intent("Qual o valor total da soma das notas fiscais?")
    assert q_soma["is_global_or_multi_doc"] is True
    assert q_soma["is_aggregation"] is True

    q_filtro = classify_query_intent("Quais notas possuem mais de sete mil reais?")
    assert q_filtro["is_global_or_multi_doc"] is True
    assert q_filtro["is_comparison"] is True

    q_especifica = classify_query_intent("Qual o valor da nota 1001?")
    assert q_especifica["specific_invoice"] == "NF-001001"
    assert q_especifica["is_global_or_multi_doc"] is False

    q_fora_escopo = classify_query_intent("Quem ganhou a copa do mundo de 2022?")
    assert q_fora_escopo["is_global_or_multi_doc"] is False
    assert q_fora_escopo["is_aggregation"] is False

def test_search_similar_retrieves_all_headers_for_global_queries():
    emb = generate_single_embedding("Qual o valor total da soma das notas fiscais?")
    results = db_store.search_similar(emb, top_k=5, base_id="default", query_text="Qual o valor total da soma das notas fiscais?")
    
    assert len(results) >= 4
    invoices_found = {r.get("invoice_number") for r in results}
    # As 4 notas devem estar presentes
    assert "NF-001001" in invoices_found
    assert "NF-001002" in invoices_found
    assert "NF-001003" in invoices_found
    assert "NF-001004" in invoices_found

def test_query_rag_sum():
    res = query_rag(QueryRequest(question="Qual o valor total da soma das notas fiscais?"))
    assert res["pipeline"]["candidates_found"] >= 4
    # A soma 46500 + 119700 + 16595 + 16091 = 198886.00
    assert "198" in res["answer"]
    assert "886" in res["answer"]

def test_query_rag_comparison_filter():
    res = query_rag(QueryRequest(question="Quais notas possuem mais de sete mil reais?"))
    assert res["pipeline"]["candidates_found"] >= 4
    # Todas as 4 notas ultrapassam R$ 7.000
    ans = res["answer"]
    assert "NF-001001" in ans
    assert "NF-001002" in ans
    assert "NF-001003" in ans
    assert "NF-001004" in ans

def test_query_rag_anti_hallucination():
    res = query_rag(QueryRequest(question="Quem ganhou a copa do mundo de 2022?"))
    assert res["answer"] == "Sem dados disponiveis na base"
