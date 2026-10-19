import os

from backend.app import main


def test_process_pdf_document_moves_file_from_raw_to_gold_after_success(monkeypatch, tmp_path):
    raw_dir = tmp_path / "invoices" / "raw"
    gold_dir = tmp_path / "invoices" / "gold"
    raw_dir.mkdir(parents=True)
    gold_dir.mkdir(parents=True)

    source_file = raw_dir / "invoice_001.pdf"
    source_file.write_bytes(b"fake-pdf")

    monkeypatch.setattr(main, "RAW_INVOICES_DIR", str(raw_dir))
    monkeypatch.setattr(main, "GOLD_INVOICES_DIR", str(gold_dir))

    monkeypatch.setattr(
        main,
        "extract_text_and_tables_from_pdf",
        lambda file_path: {
            "used_ocr": False,
            "parsed_fields": {
                "numero_nota": "NF-001",
                "data_emissao": "2024-01-01",
                "fornecedor": "ACME",
                "cnpj": "12.345.678/0001-99",
                "cliente": "Cliente X",
                "cliente_cnpj": "98.765.432/0001-88",
                "valor_total": 1250.50,
            },
            "raw_text": "nota fiscal de teste",
        },
    )

    monkeypatch.setattr(main, "chunk_document", lambda doc_id, numero_nota, parsed, raw_text: [{
        "chunk_id": "chunk_1",
        "chunk_index": 0,
        "chunk_type": "body",
        "token_count": 4,
        "content": "conteudo do chunk",
        "invoice_number": numero_nota,
    }])

    monkeypatch.setattr(main, "generate_embeddings", lambda chunk_texts: [[0.1, 0.2, 0.3] for _ in chunk_texts])
    monkeypatch.setattr(main.db_store, "save_document_and_chunks", lambda *args, **kwargs: None)

    trace = main.process_pdf_document(str(source_file), "invoice_001.pdf", "doc_001", "default")

    assert trace["filename"] == "invoice_001.pdf"
    assert not source_file.exists()
    moved_file = gold_dir / "invoice_001.pdf"
    assert moved_file.exists()
