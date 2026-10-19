# 🧠 Sistema RAG Didático & Observável

> Plataforma educacional completa para compreensão, rastreabilidade e visualização visual de cada etapa de um pipeline **RAG (Retrieval-Augmented Generation)** — da ingestão de documentos fiscais e OCR até o retrieval vetorial e resposta com LLM.

---

## 📋 Sumário

- [Visão Geral](#-visão-geral)
- [Arquitetura do Pipeline](#-arquitetura-do-pipeline)
- [Tecnologias Utilizadas](#-tecnologias-utilizadas)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Pré-requisitos](#-pré-requisitos)
- [Guia de Instalação e Execução Local](#-guia-de-instalação-e-execução-local)
  - [1. Clonar o Repositório](#1-clonar-o-repositório)
  - [2. Configurar as Variáveis de Ambiente](#2-configurar-as-variáveis-de-ambiente)
  - [3. Configurar e Iniciar o Backend (FastAPI)](#3-configurar-e-iniciar-o-backend-fastapi)
  - [4. Configurar e Iniciar o Frontend (Next.js)](#4-configurar-e-iniciar-o-frontend-nextjs)
  - [5. (Opcional) Configurar o Banco no Supabase](#5-opcional-configurar-o-banco-no-supabase)
  - [6. (Opcional) Gerar Notas Fiscais Fictícias](#6-opcional-gerar-notas-fiscais-fictícias)
- [Como Utilizar a Aplicação](#-como-utilizar-a-aplicação)
- [Endpoints da API Backend](#-endpoints-da-api-backend)
- [Resolução de Problemas (Troubleshooting)](#-resolução-de-problemas-troubleshooting)
- [Licença](#-licença)

---

## 🎯 Visão Geral

Este projeto foi concebido para transformar a "caixa-preta" de sistemas RAG em um processo transparente e interativo. Desenvolvido para fins educacionais e de engenharia de software, ele permite analisar cada sub-etapa do pipeline em tempo real:

1. **Extração de Documentos & OCR**: Processamento de PDFs nativos e digitalizados via `pdfplumber` e `pypdfium2` com fallback para OCR (`pytesseract`).
2. **Extração de Entidades Estruturadas**: Parsing de metadados críticos (número da nota, datas, CNPJ, fornecedor, cliente, valores e itens).
3. **Tokenização Didática**: Segmentação visual de tokens com contagem precisa via `tiktoken`.
4. **Chunking Semântico & Estruturado**: Quebra de documentos preservando cabeçalhos e tabelas, com metadados por chunk e controle de overlap.
5. **Geração de Embeddings Locais**: Vetorização semântica de alta performance com `FastEmbed` (`BAAI/bge-small-en-v1.5`, 384 dimensões) rodando localmente via ONNX Runtime (sem custo por token de embedding).
6. **Armazenamento Vetorial Duplo**:
   - **Nuvem**: Supabase PostgreSQL com extensão `pgvector` e índice HNSW para busca por similaridade de cosseno.
   - **Local (Fallback Resiliente)**: Armazenamento vetorial estruturado em JSON com algoritmo híbrido de similaridade de cosseno e boost léxico (BM25 simplificado).
7. **Mecanismo Anti-Alucinação Estrito**: Se a similaridade máxima dos candidatos recuperados for inferior ao limiar calibrado (0.60), o sistema encerra a resposta como *"Sem dados disponíveis na base"*, poupando custos de LLM e eliminando alucinações.
8. **Construção do Prompt Aumentado**: Injeção do contexto recuperado em um template de prompt rigoroso.
9. **Geração com LLM**: Invocação de modelos de ponta via OpenRouter API (padrão: `openrouter/auto`).

---

## 🏗️ Arquitetura do Pipeline

```
[ Ingestão ]
   │
   ├──> PDF (DANFE / Nota Fiscal)
   │     │
   │     ├──> Extração de Texto / Tabelas (pdfplumber / pypdfium2 / pytesseract OCR)
   │     ├──> Parser de Metadados Fiscais (Nº, Data, Fornecedor, Valor, etc.)
   │     ├──> Tokenização Didática (tiktoken)
   │     ├──> Chunking Estruturado com Metadados
   │     └──> Geração de Embeddings (FastEmbed - 384 dim)
   │           │
   │           ├──> Supabase pgvector (Nuvem)
   │           └──> local_vector_store.json (Espelho Local)

[ Consulta ]
   │
   ├──> Pergunta do Usuário
   │     │
   │     ├──> Tokenização e Embedding da Consulta (FastEmbed)
   │     ├──> Busca Vetorial (Similaridade Cosseno + Boost Léxico, Top-K)
   │     │
   │     ├──> [Similaridade < 0.60?] ──SIM──> "Sem dados disponíveis na base" (Stop)
   │     │                                      (Sem consumo de LLM)
   │     └──> [Similaridade >= 0.60] ──NÃO─> Montagem do Prompt Aumentado
   │                                           │
   │                                           └──> LLM (OpenRouter API) ──> Resposta Final na UI
```

---

## 🛠️ Tecnologias Utilizadas

### Backend
- **Linguagem**: [Python 3.11+](https://www.python.org/)
- **Framework Web**: [FastAPI](https://fastapi.tiangolo.com/) com [Uvicorn](https://www.uvicorn.org/)
- **Validação de Dados**: [Pydantic v2](https://docs.pydantic.dev/)
- **Embeddings**: [FastEmbed](https://github.com/qdrant/fastembed) (`BAAI/bge-small-en-v1.5`, 384 dimensões, ONNX Runtime)
- **Tokenização**: [tiktoken](https://github.com/openai/tiktoken)
- **Extração de PDF e OCR**:
  - [pdfplumber](https://github.com/jsvine/pdfplumber)
  - [pypdfium2](https://github.com/pypdfium2-team/pypdfium2)
  - [pytesseract](https://github.com/madmaze/pytesseract) & [Pillow](https://python-pillow.org/)
- **Geração de Documentos**: [ReportLab](https://www.reportlab.com/)
- **Conectores e Clientes**: `supabase-py`, `requests`, `python-dotenv`

### Frontend
- **Framework**: [Next.js 16](https://nextjs.org/) (App Router, Turbopack)
- **Biblioteca Base**: [React 19](https://react.dev/)
- **Tipagem**: [TypeScript](https://www.typescriptlang.org/)
- **Estilização**: [Tailwind CSS v4](https://tailwindcss.com/)
- **Ícones**: [Lucide React](https://lucide.dev/)

### Banco de Dados & Infraestrutura
- **Banco Vetorial em Nuvem**: [Supabase](https://supabase.com/) (PostgreSQL 15+ com extensão `pgvector` e índice HNSW)
- **Armazenamento Local**: Espelho de vetores em JSON (`data/local_vector_store.json`)
- **Provedor de LLM**: [OpenRouter](https://openrouter.ai/) (`openrouter/auto`)

---

## 📂 Estrutura do Projeto

```text
RAG/
├── backend/
│   └── app/
│       ├── __init__.py
│       ├── chunker.py           # Divisão em chunks semânticos e tokenização
│       ├── db_store.py          # Gestão do Supabase (pgvector) e fallback local
│       ├── embedder.py          # Geração de embeddings com FastEmbed
│       ├── extractor.py         # Extração de PDFs, tabelas e fallback OCR
│       ├── llm_client.py        # Montagem do prompt aumentado e cliente OpenRouter
│       └── main.py              # Endpoints FastAPI e orquestração do pipeline
├── data/
│   ├── invoices/                # PDFs didáticos de notas fiscais pré-geradas
│   ├── uploads/                 # Diretório para upload de novos PDFs
│   └── local_vector_store.json  # Base vetorial local (fallback resiliente)
├── frontend/
│   ├── public/                  # Arquivos estáticos
│   ├── src/
│   │   └── app/
│   │       ├── globals.css      # Estilização global e tokens Tailwind CSS
│   │       ├── layout.tsx       # Layout raiz da aplicação
│   │       └── page.tsx         # Dashboard completo didático (Aba Consulta, Ingestão, Docs)
│   ├── package.json             # Dependências e scripts do frontend
│   └── tsconfig.json            # Configuração do TypeScript
├── .env.example                 # Modelo de variáveis de ambiente
├── .gitignore                   # Arquivos ignorados pelo Git
├── generate_invoices.py         # Script para geração automática dos PDFs fictícios
├── requirements.txt             # Dependências Python do backend
├── supabase_schema.sql          # Script SQL para criação de tabelas e RPC no Supabase
└── README.md                    # Documentação do projeto
```

---

## ⚙️ Pré-requisitos

Antes de iniciar, certifique-se de possuir instalado em seu ambiente:

1. **Python**: Versão `3.11`, `3.12` ou `3.13`.
2. **Node.js**: Versão `18.x`, `20.x` ou `22.x+` (com o utilitário `npm`).
3. **Git**: Para clonar o repositório.
4. *(Opcional)* **Tesseract OCR**: Necessário apenas caso queira realizar OCR em imagens digitalizadas escaneadas sem camada de texto vetorial.

---

## 🚀 Guia de Instalação e Execução Local

### 1. Clonar o Repositório

```bash
git clone https://github.com/Hannower/RAG.git
cd RAG
```

---

### 2. Configurar as Variáveis de Ambiente

Crie uma cópia do arquivo `.env.example` nomeando-a como `.env` na raiz do projeto:

#### No Windows (PowerShell):
```powershell
Copy-Item .env.example .env
```

#### No Linux/macOS (Bash):
```bash
cp .env.example .env
```

Abra o arquivo `.env` e preencha com suas chaves de API:

```env
# Configurações do Supabase (Opcional se utilizar o armazenamento local)
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_PUBLISHABLE_KEY=sua_chave_publica
SUPABASE_SECRET_KEY=sua_chave_secreta
SUPABASE_JWKS_URL=https://seu-projeto.supabase.co/auth/v1/.well-known/jwks.json

# Chave da OpenRouter para geração de respostas com a LLM
OPENROUTER_API_KEY=sk-or-v1-sua-chave-aqui
```

> 💡 **Nota:** Se você não configurar o Supabase, o sistema ativará automaticamente o **armazenamento vetorial local em JSON** (`data/local_vector_store.json`), funcionando 100% sem falhas.

---

### 3. Configurar e Iniciar o Backend (FastAPI)

Abra um terminal na raiz do projeto:

#### Passo 3.1: Criar e ativar o ambiente virtual

**No Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
*(Caso o PowerShell bloqueie a execução de scripts, execute `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` antes).*

**No Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Passo 3.2: Instalar as dependências Python
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Passo 3.3: Iniciar o servidor FastAPI
```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

O backend estará acessível em:
- **API Base**: `http://127.0.0.1:8000`
- **Documentação Swagger Interativa**: `http://127.0.0.1:8000/docs`
- **Verificação de Saúde**: `http://127.0.0.1:8000/api/health`

---

### 4. Configurar e Iniciar o Frontend (Next.js)

Abra um **segundo terminal** e navegue até a pasta `frontend`:

```bash
cd frontend
```

#### Passo 4.1: Instalar dependências do Node.js
```bash
npm install
```
*(No Windows PowerShell, caso o comando `npm` apresente bloqueio por política de segurança de script, utilize `npm.cmd install`)*.

#### Passo 4.2: Iniciar o servidor de desenvolvimento
```bash
npm run dev
```
*(Ou `npm.cmd run dev` no Windows PowerShell)*.

O frontend estará rodando em:
- **Painel Didático RAG**: **[http://localhost:3000](http://localhost:3000)**

---

### 5. (Opcional) Configurar o Banco no Supabase

Caso deseje persistir os vetores diretamente no Supabase em vez do armazenamento local:

1. Acesse o painel do seu projeto no [Supabase](https://supabase.com/).
2. Abra o menu **SQL Editor**.
3. Copie o conteúdo do arquivo [`supabase_schema.sql`](./supabase_schema.sql).
4. Cole no editor e clique em **Run**.
5. O script criará a extensão `vector`, as tabelas `rag_bases`, `rag_documents`, `rag_invoice_items`, `rag_chunks`, o índice HNSW e a função RPC `match_rag_chunks`.

---

### 6. (Opcional) Gerar Notas Fiscais Fictícias

O projeto já inclui 4 notas fiscais pré-geradas na pasta `data/invoices/`. Caso queira recriá-las ou gerar novos modelos via ReportLab:

```bash
python generate_invoices.py
```

---

## 🖥️ Como Utilizar a Aplicação

Acesse **`http://localhost:3000`** para interagir com o Dashboard:

### 1. 🔍 Aba "Consulta RAG"
- Digite uma pergunta em linguagem natural sobre as notas fiscais (ex.: *"Qual o valor total da nota fiscal da TechSupply?"* ou *"Quais itens foram comprados na NF-001002?"*).
- Ajuste o controle de **Top-K** (candidatos a recuperar).
- Clique em **"Executar Pipeline RAG"**.
- Acompanhe cada etapa nos cards interativos:
  1. **Tokenização**: Tokens identificados e contagem total.
  2. **Embedding**: Vetor denso numérico normalizado de 384 dimensões.
  3. **Retrieval**: Chunks candidatos ordenados por similaridade com preview do conteúdo.
  4. **Prompt Aumentado**: O prompt final montado com as regras anti-alucinação.
  5. **Resposta da LLM**: A resposta sintética gerada com métricas de tempo e tokens consumidos.

### 2. 📥 Aba "Ingestão Didática"
- **Ingestão Pré-Configurada**: Clique em *"Ingerir 4 Notas Fiscais Didáticas"* para processar o lote de amostra.
- **Upload Manual**: Envie seu próprio arquivo PDF de fatura ou nota fiscal e acompanhe a extração estruturada de campos e geração de chunks.

### 3. 📚 Aba "Base de Conhecimento"
- Visualize todos os documentos atualmente indexados, números das notas, fornecedores, destinatários e valores totais.

---

## 📡 Endpoints da API Backend

| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Status da API, conexão com Supabase e modelos configurados |
| `GET` | `/api/bases` | Lista bases/coleções de documentos disponíveis |
| `GET` | `/api/documents?base_id=default` | Lista todos os documentos ingeridos e seus metadados |
| `POST` | `/api/query` | Executa o pipeline de consulta RAG completo |
| `POST` | `/api/ingest/default-invoices` | Ingestão em lote dos PDFs fictícios padrão |
| `POST` | `/api/ingest/upload` | Upload e ingestão de novos arquivos PDF |

#### Exemplo de Consulta via Terminal (`curl` / PowerShell):

```powershell
$body = @{
    question = "Qual o valor total da nota fiscal da TechSupply?"
    top_k = 3
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/query" -Method Post -Body $body -ContentType "application/json"
```

---

## 🔧 Resolução de Problemas (Troubleshooting)

### 1. Erro de Script Bloqueado no Windows (`PSSecurityException`)
- **Causa**: Política de execução restritiva do PowerShell para arquivos `.ps1`.
- **Solução**: Use comandos com extensão explícita `.cmd` (ex.: `npm.cmd run dev`) ou desbloqueie a sessão atual com:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```

### 2. Supabase não configurado ou tabelas ausentes
- **Comportamento**: O sistema emite um aviso no terminal e chaveia automaticamente para o **armazenamento local espelhado** (`data/local_vector_store.json`).
- **Ação**: Nenhuma ação obrigatória. O sistema continua operando normalmente. Para habilitar o Supabase, execute o script [`supabase_schema.sql`](./supabase_schema.sql) no painel do Supabase.

### 3. Porta 8000 ou 3000 já em uso
- Verifique os processos ativos:
  ```powershell
  Get-NetTCPConnection -LocalPort 8000, 3000 -ErrorAction SilentlyContinue
  ```
- Para especificar outra porta no FastAPI: `uvicorn backend.app.main:app --port 8080`.
- Para especificar outra porta no Next.js: `npm run dev -- -p 3001`.

---

## 📄 Licença

Projeto desenvolvido para fins educacionais e didáticos. Distribuído sob a licença MIT. Sinta-se livre para utilizar, modificar e estender.