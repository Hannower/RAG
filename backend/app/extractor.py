import os
import re
from typing import List, Dict, Any, Optional
import pypdfium2 as pdfium
import pdfplumber
import pytesseract

def extract_text_and_tables_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Executa a leitura do documento:
    1. Tenta extração direta de texto estruturado com pdfplumber (e tabelas).
    2. Se o texto for vazio/insuficiente, aplica OCR via pypdfium2 + pytesseract.
    3. Retorna o texto extraído, tabelas detectadas e método utilizado.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {pdf_path}")
    
    extracted_text = ""
    tables_found = []
    used_ocr = False
    
    # 1. Tentativa de extração direta de texto nativo do PDF
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
                
                # Extrai tabelas se existirem
                page_tables = page.extract_tables()
                if page_tables:
                    for tbl in page_tables:
                        tables_found.append({"page": page_num + 1, "data": tbl})
    except Exception as e:
        print(f"Aviso ao ler com pdfplumber: {e}")

    # 2. Se o texto for muito curto (< 50 caracteres), aciona OCR
    if len(extracted_text.strip()) < 50:
        used_ocr = True
        try:
            pdf_doc = pdfium.PdfDocument(pdf_path)
            ocr_text = ""
            for i, page in enumerate(pdf_doc):
                image = page.render(scale=2.0).to_pil()
                try:
                    text_page = pytesseract.image_to_string(image, lang='por+eng')
                    ocr_text += text_page + "\n"
                except Exception as ocr_err:
                    ocr_text += f"[OCR não executado: {ocr_err}]\n"
            if len(ocr_text.strip()) > len(extracted_text.strip()):
                extracted_text = ocr_text
        except Exception as pdfium_err:
            print(f"Aviso no fallback de OCR: {pdfium_err}")

    # 3. Parse e identificação de campos relevantes da Nota Fiscal
    parsed_fields = parse_invoice_fields(extracted_text)

    return {
        "raw_text": extracted_text.strip(),
        "tables": tables_found,
        "used_ocr": used_ocr,
        "parsed_fields": parsed_fields
    }

def parse_invoice_fields(text: str) -> Dict[str, Any]:
    """
    Identifica de forma determinística os campos relevantes da nota fiscal fictícia:
    - Número da nota
    - Data de emissão
    - Fornecedor
    - CNPJ do Fornecedor
    - Cliente
    - CNPJ do Cliente
    - Valor total
    - Itens
    """
    fields: Dict[str, Any] = {
        "numero_nota": "Desconhecido",
        "data_emissao": "",
        "fornecedor": "",
        "cnpj": "",
        "cliente": "",
        "cliente_cnpj": "",
        "valor_total": 0.0,
        "itens": []
    }

    # Regex Número da Nota
    num_match = re.search(r"N[uú]mero\s+da\s+Nota:\s*(NF-\d+|\d+)", text, re.IGNORECASE)
    if num_match:
        fields["numero_nota"] = num_match.group(1).strip()

    # Regex Data de Emissão
    date_match = re.search(r"Data\s+de\s+Emiss[aã]o:\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
    if date_match:
        fields["data_emissao"] = date_match.group(1).strip()

    # Regex Fornecedor
    forn_match = re.search(r"Fornecedor:\s*([^\n\r]+?)(?:\s+CNPJ|\n|$)", text, re.IGNORECASE)
    if forn_match:
        fields["fornecedor"] = forn_match.group(1).strip()

    # Regex CNPJ
    cnpj_match = re.search(r"CNPJ(?:\s+Emitente)?:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", text, re.IGNORECASE)
    if cnpj_match:
        fields["cnpj"] = cnpj_match.group(1).strip()

    # Regex Cliente
    cli_match = re.search(r"Cliente(?:\s*/\s*Destinat[aá]rio)?:\s*([^\n\r]+?)(?:\s+CNPJ|\n|$)", text, re.IGNORECASE)
    if cli_match:
        fields["cliente"] = cli_match.group(1).strip()

    # Regex CNPJ Cliente
    cli_cnpj_match = re.search(r"CNPJ\s+Destinat[aá]rio:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", text, re.IGNORECASE)
    if cli_cnpj_match:
        fields["cliente_cnpj"] = cli_cnpj_match.group(1).strip()

    # Regex Valor Total
    total_match = re.search(r"VALOR\s+TOTAL(?:\s+DA\s+NOTA\s+FISCAL)?\s*R\$\s*([\d\.,]+)", text, re.IGNORECASE)
    if total_match:
        val_str = total_match.group(1).strip().replace('.', '').replace(',', '.')
        try:
            fields["valor_total"] = float(val_str)
        except ValueError:
            pass

    # Extração de itens (linhas com descrição e valores)
    lines = text.splitlines()
    for line in lines:
        # Padrão: Descrição Qtd R$ Valor_Unit R$ Valor_Total
        item_match = re.search(r"^(.+?)\s+(\d+)\s+R\$\s*([\d\.,]+)\s+R\$\s*([\d\.,]+)$", line.strip())
        if item_match:
            desc = item_match.group(1).strip()
            qtd = int(item_match.group(2))
            v_unit = float(item_match.group(3).replace('.', '').replace(',', '.'))
            v_total = float(item_match.group(4).replace('.', '').replace(',', '.'))
            fields["itens"].append({
                "descricao": desc,
                "quantidade": qtd,
                "valor_unitario": v_unit,
                "valor_total": v_total
            })

    return fields
