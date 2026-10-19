import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

INVOICES = [
    {
        "filename": "nota_fiscal_1001.pdf",
        "numero_nota": "NF-001001",
        "data_emissao": "12/01/2026",
        "fornecedor": "TechSupply Equipamentos de Informatica Ltda",
        "cnpj": "12.345.678/0001-90",
        "cliente": "Escola e Faculdade Teophilo RAG Edu",
        "cliente_cnpj": "98.765.432/0001-10",
        "itens": [
            ("Notebook Dell Inspiron 15 i7 16GB SSD 512GB", 5, 4500.00, 22500.00),
            ("Monitor LG UltraWide 29 Polegadas Full HD", 10, 1200.00, 12000.00),
            ("Teclado Mecanico Logitech MX Keys Wireless", 10, 650.00, 6500.00),
            ("Mouse Optico Ergonomico Logitech MX Master 3S", 10, 550.00, 5500.00),
        ],
        "valor_total": 46500.00,
        "observacoes": "Entrega realizada no bloco A - Laboratorio de Inteligencia Artificial e RAG. Garantia de 12 meses direto com o fabricante."
    },
    {
        "filename": "nota_fiscal_1002.pdf",
        "numero_nota": "NF-001002",
        "data_emissao": "05/02/2026",
        "fornecedor": "CloudData Servicos de Hospedagem e Redes S.A.",
        "cnpj": "23.456.789/0001-81",
        "cliente": "Escola e Faculdade Teophilo RAG Edu",
        "cliente_cnpj": "98.765.432/0001-10",
        "itens": [
            ("Servidor Rack Dell PowerEdge R750 Xeon Silver", 2, 38000.00, 76000.00),
            ("Switch Gerenciavel Cisco Catalyst 48 Portas Gigabit", 3, 8500.00, 25500.00),
            ("Nobreak Senoidal APC Smart-UPS 3000VA Bivolt", 2, 7200.00, 14400.00),
            ("Cabo de Rede Furukawa Cat6 Bobina 305m", 4, 950.00, 3800.00),
        ],
        "valor_total": 119700.00,
        "observacoes": "Equipamentos destinados a infraestrutura do Data Center para modelos de Embeddings e Banco Vetorial Supabase."
    },
    {
        "filename": "nota_fiscal_1003.pdf",
        "numero_nota": "NF-001003",
        "data_emissao": "18/02/2026",
        "fornecedor": "Papelaria e Suprimentos Graficos Brasil Express",
        "cnpj": "34.567.890/0001-72",
        "cliente": "Escola e Faculdade Teophilo RAG Edu",
        "cliente_cnpj": "98.765.432/0001-10",
        "itens": [
            ("Papel Sulfite A4 Report 75g Caixa com 10 Resmas", 25, 280.00, 7000.00),
            ("Cartucho de Toner HP LaserJet Original Preto CF258A", 8, 890.00, 7120.00),
            ("Quadro Branco Magnetico Aluminio 200x120cm", 4, 450.00, 1800.00),
            ("Kit Canetas Marcador para Quadro Branco Cores Sortidas", 15, 45.00, 675.00),
        ],
        "valor_total": 16595.00,
        "observacoes": "Material didatico e administrativo para as salas de aula e workshops presenciais de RAG."
    },
    {
        "filename": "nota_fiscal_1004.pdf",
        "numero_nota": "NF-001004",
        "data_emissao": "03/03/2026",
        "fornecedor": "Livraria e Editora Tecnologica DeepData",
        "cnpj": "45.678.901/0001-63",
        "cliente": "Escola e Faculdade Teophilo RAG Edu",
        "cliente_cnpj": "98.765.432/0001-10",
        "itens": [
            ("Livro: Construindo Sistemas RAG na Pratica com Python", 30, 149.90, 4497.00),
            ("Livro: Engenharia de Prompts e Agentes Inteligentes", 30, 129.90, 3897.00),
            ("Livro: Bancos de Dados Vetoriais e Busca Semantica PGVECTOR", 30, 139.90, 4197.00),
            ("Licenca Didatica Anual da Colecao Digital de Artigos RAG", 1, 3500.00, 3500.00),
        ],
        "valor_total": 16091.00,
        "observacoes": "Aquisicao de bibliografia basica e complementar para a disciplina de Engenharia de Dados e Recuperacao de Informacao."
    }
]

def generate_pdf(data, output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569'),
        spaceAfter=15
    )
    
    bold_style = ParagraphStyle(
        'DocBold',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1E293B')
    )

    story = []

    # Cabeçalho
    story.append(Paragraph("DOCUMENTO FISCAL DIDÁTICO — DANFE SIMULADA", title_style))
    story.append(Paragraph("SISTEMA RAG DIDÁTICO | RAG + TEOPHILO", subtitle_style))
    story.append(Spacer(1, 10))

    # Tabela de dados gerais
    header_data = [
        [
            Paragraph(f"<b>Número da Nota:</b> {data['numero_nota']}", body_style),
            Paragraph(f"<b>Data de Emissão:</b> {data['data_emissao']}", body_style)
        ],
        [
            Paragraph(f"<b>Fornecedor:</b> {data['fornecedor']}", body_style),
            Paragraph(f"<b>CNPJ Emitente:</b> {data['cnpj']}", body_style)
        ],
        [
            Paragraph(f"<b>Cliente / Destinatário:</b> {data['cliente']}", body_style),
            Paragraph(f"<b>CNPJ Destinatário:</b> {data['cliente_cnpj']}", body_style)
        ]
    ]
    t_header = Table(header_data, colWidths=[280, 250])
    t_header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 15))

    # Itens da Nota
    story.append(Paragraph("ITENS DA NOTA FISCAL", bold_style))
    story.append(Spacer(1, 6))

    items_table_data = [
        [
            Paragraph("<b>Descrição do Produto / Serviço</b>", body_style),
            Paragraph("<b>Qtd</b>", body_style),
            Paragraph("<b>Valor Unit. (R$)</b>", body_style),
            Paragraph("<b>Valor Total (R$)</b>", body_style)
        ]
    ]

    for desc, qtd, vu, vt in data['itens']:
        items_table_data.append([
            Paragraph(desc, body_style),
            Paragraph(str(qtd), body_style),
            Paragraph(f"R$ {vu:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), body_style),
            Paragraph(f"R$ {vt:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), body_style)
        ])

    items_table_data.append([
        Paragraph("<b>VALOR TOTAL DA NOTA FISCAL</b>", bold_style),
        Paragraph("", body_style),
        Paragraph("", body_style),
        Paragraph(f"<b>R$ {data['valor_total']:,.2f}</b>".replace(',', 'X').replace('.', ',').replace('X', '.'), bold_style)
    ])

    t_items = Table(items_table_data, colWidths=[290, 45, 95, 100])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E2E8F0')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#94A3B8')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F1F5F9')),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 15))

    # Observações adicionais
    obs_data = [
        [Paragraph("<b>Observações e Dados Adicionais:</b>", bold_style)],
        [Paragraph(data['observacoes'], body_style)]
    ]
    t_obs = Table(obs_data, colWidths=[530])
    t_obs.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_obs)

    doc.build(story)
    print(f"Gerado: {output_path}")

if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "data", "invoices", "raw")
    os.makedirs(out_dir, exist_ok=True)
    for inv in INVOICES:
        path = os.path.join(out_dir, inv["filename"])
        generate_pdf(inv, path)
    print("Todos os 4 PDFs fictícios foram criados em data/invoices/raw com sucesso!")
