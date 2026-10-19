"use client";

import React, { useState, useEffect } from "react";
import {
  Brain,
  Database,
  FileText,
  Search,
  Sparkles,
  Layers,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Cpu,
  RefreshCw,
  Upload,
  Info,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  BookOpen,
} from "lucide-react";

interface HealthStatus {
  status: string;
  supabase_connected: boolean;
  embedding_model: string;
  llm_model: string;
}

interface TokenVisual {
  id: number;
  piece: string;
}

interface Candidate {
  id?: string;
  chunk_id?: string;
  document_id: string;
  chunk_index: number;
  content: string;
  similarity: number;
  invoice_number?: string;
  token_count?: number;
}

interface QueryPipeline {
  tokenization: {
    token_count: number;
    tokens_visual: TokenVisual[];
  };
  embedding_preview: number[];
  embedding_dimension: number;
  top_k: number;
  candidates_found: number;
  candidates: Candidate[];
}

interface QueryResponse {
  question: string;
  pipeline: QueryPipeline;
  augmented_prompt: string | null;
  answer: string;
  model_info: string;
  token_usage?: {
    total_tokens?: number;
    prompt_tokens?: number;
    completion_tokens?: number;
  };
}

interface DocumentInfo {
  id: string;
  filename: string;
  invoice_number: string;
  supplier_name: string;
  customer_name: string;
  total_amount: number;
  issue_date: string;
}

const API_BASE = "http://127.0.0.1:8000";

export default function RAGDashboard() {
  const [activeTab, setActiveTab] = useState<"query" | "ingest" | "knowledge">("query");
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(true);

  // Consulta State
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(5);
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [activeStep, setActiveStep] = useState<number>(5);
  const [promptCopied, setPromptCopied] = useState(false);

  // Ingestão State
  const [ingestingDefault, setIngestingDefault] = useState(false);
  const [ingestLogs, setIngestLogs] = useState<any[]>([]);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null);

  // Documentos State
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);

  // Busca inicial de saúde da API e documentos
  useEffect(() => {
    fetchHealth();
    fetchDocuments();
  }, []);

  const fetchHealth = async () => {
    try {
      setLoadingHealth(true);
      const res = await fetch(`${API_BASE}/api/health`);
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      }
    } catch (err) {
      console.error("Erro ao verificar health:", err);
      setHealth(null);
    } finally {
      setLoadingHealth(false);
    }
  };

  const fetchDocuments = async () => {
    try {
      setLoadingDocs(true);
      const res = await fetch(`${API_BASE}/api/documents`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (err) {
      console.error("Erro ao buscar documentos:", err);
    } finally {
      setLoadingDocs(false);
    }
  };

  const handleQuery = async (queryText?: string) => {
    const q = queryText || question;
    if (!q.trim()) return;

    try {
      setQueryLoading(true);
      setQueryResult(null);
      const res = await fetch(`${API_BASE}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, top_k: topK }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Erro na consulta");
      }

      const data: QueryResponse = await res.json();
      setQueryResult(data);
      setActiveStep(5);
    } catch (err: any) {
      alert("Falha na consulta: " + err.message);
    } finally {
      setQueryLoading(false);
    }
  };

  const handleIngestDefaults = async () => {
    try {
      setIngestingDefault(true);
      const res = await fetch(`${API_BASE}/api/ingest/default-invoices`, {
        method: "POST",
      });
      const data = await res.json();
      if (res.ok) {
        setIngestLogs(data.documents_processed || []);
        fetchDocuments();
        alert(data.message);
      } else {
        alert("Erro na ingestão: " + (data.detail || "Falha"));
      }
    } catch (err: any) {
      alert("Erro ao conectar com a API: " + err.message);
    } finally {
      setIngestingDefault(false);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append("file", uploadFile);
      formData.append("base_id", "default");

      const res = await fetch(`${API_BASE}/api/ingest/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setIngestLogs((prev) => [data.document_processed, ...prev]);
        setUploadFile(null);
        fetchDocuments();
        alert(data.message);
      } else {
        alert("Erro no upload: " + (data.detail || "Falha"));
      }
    } catch (err: any) {
      alert("Erro de conexão no upload: " + err.message);
    } finally {
      setUploading(false);
    }
  };

  const copyPrompt = () => {
    if (queryResult?.augmented_prompt) {
      navigator.clipboard.writeText(queryResult.augmented_prompt);
      setPromptCopied(true);
      setTimeout(() => setPromptCopied(false), 2000);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#090d16] text-gray-100 selection:bg-blue-600 selection:text-white">
      {/* Top Navigation Bar */}
      <header className="border-b border-white/10 bg-[#0d1322]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/25">
              <Brain className="w-5 h-5 text-white animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-gray-200 to-gray-400 bg-clip-text text-transparent">
                  RAG Didático + Hannower
                </span>
                <span className="px-2 py-0.5 text-[10px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-full">
                  v1.0
                </span>
              </div>
              <p className="text-xs text-gray-400 hidden sm:block">
                Visualizador Interativo do Pipeline RAG de Notas Fiscais
              </p>
            </div>
          </div>

          {/* Status Badges */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-800/60 border border-white/5 text-xs">
              <span className="relative flex h-2 w-2">
                <span
                  className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                    health ? "bg-emerald-400" : "bg-red-400"
                  }`}
                ></span>
                <span
                  className={`relative inline-flex rounded-full h-2 w-2 ${
                    health ? "bg-emerald-500" : "bg-red-500"
                  }`}
                ></span>
              </span>
              <span className="font-medium">
                {health ? "Backend Online" : "Backend Offline"}
              </span>
            </div>

            <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-800/60 border border-white/5 text-xs">
              <Database className="w-3.5 h-3.5 text-indigo-400" />
              <span>
                {health?.supabase_connected ? (
                  <span className="text-emerald-400">Supabase PGVector</span>
                ) : (
                  <span className="text-amber-400" title="Fallback local ativo">
                    VectorStore Local
                  </span>
                )}
              </span>
            </div>

            <button
              onClick={() => {
                fetchHealth();
                fetchDocuments();
              }}
              className="p-1.5 text-gray-400 hover:text-white rounded-lg hover:bg-white/5 transition"
              title="Atualizar status"
            >
              <RefreshCw className={`w-4 h-4 ${loadingHealth ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Tab Selector */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex gap-2 pt-1 border-t border-white/5">
          <button
            onClick={() => setActiveTab("query")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition ${
              activeTab === "query"
                ? "border-blue-500 text-blue-400 bg-blue-500/5"
                : "border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-600"
            }`}
          >
            <Search className="w-4 h-4" />
            Consulta & Chat RAG
          </button>
          <button
            onClick={() => setActiveTab("ingest")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition ${
              activeTab === "ingest"
                ? "border-indigo-500 text-indigo-400 bg-indigo-500/5"
                : "border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-600"
            }`}
          >
            <Layers className="w-4 h-4" />
            Pipeline de Ingestão & Chunks
          </button>
          <button
            onClick={() => setActiveTab("knowledge")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition ${
              activeTab === "knowledge"
                ? "border-purple-500 text-purple-400 bg-purple-500/5"
                : "border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-600"
            }`}
          >
            <FileText className="w-4 h-4" />
            Base Documental ({documents.length})
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {/* ========================================================================= */}
        {/* TAB 1: CONSULTA & CHAT RAG */}
        {/* ========================================================================= */}
        {activeTab === "query" && (
          <div className="space-y-6">
            {/* Banner Didático */}
            <div className="glass-panel p-5 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-l-4 border-l-blue-500">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-blue-400" />
                  <h2 className="text-base font-semibold text-white">
                    Como funciona esta etapa de Consulta RAG?
                  </h2>
                </div>
                <p className="text-sm text-gray-400 max-w-3xl">
                  A sua pergunta é tokenizada com <span className="text-blue-300">tiktoken</span>, convertida em um vetor de 384 dimensões via <span className="text-blue-300">FastEmbed</span>, comparada aos chunks de notas fiscais usando similaridade de cosseno, e submetida ao LLM com regra estrita anti-alucinação.
                </p>
              </div>
              <div className="flex items-center gap-3">
                <label className="text-xs text-gray-400 font-medium">Top-K Chunks:</label>
                <select
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  className="bg-gray-800 border border-white/10 rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none focus:border-blue-500"
                >
                  <option value={3}>Top 3</option>
                  <option value={5}>Top 5 (Padrão)</option>
                  <option value={8}>Top 8</option>
                </select>
              </div>
            </div>

            {/* Input Box e Perguntas Prontas */}
            <div className="glass-panel p-6 rounded-2xl space-y-4">
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleQuery()}
                    placeholder="Digite sua dúvida sobre as notas fiscais (ex: Qual o valor total da NF-001001?)..."
                    className="w-full bg-gray-900/90 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition"
                  />
                  <Search className="w-4 h-4 text-gray-400 absolute right-4 top-3.5" />
                </div>
                <button
                  onClick={() => handleQuery()}
                  disabled={queryLoading || !question.trim()}
                  className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white font-medium text-sm rounded-xl transition flex items-center gap-2 shadow-lg shadow-blue-500/20"
                >
                  {queryLoading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Consultando...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Consultar RAG
                    </>
                  )}
                </button>
              </div>

              {/* Botões de Teste Didático */}
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <span className="text-xs text-gray-400 font-medium">Testar cada nota fiscal:</span>
                <button
                  onClick={() => {
                    const q = "Qual o valor total e produtos da nota NF-001001?";
                    setQuestion(q);
                    handleQuery(q);
                  }}
                  className="text-xs bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 border border-blue-500/20 rounded-lg px-2.5 py-1 transition"
                >
                  💡 NF-001001 (TechSupply)
                </button>
                <button
                  onClick={() => {
                    const q = "Qual o valor total e produtos da nota NF-001002?";
                    setQuestion(q);
                    handleQuery(q);
                  }}
                  className="text-xs bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/20 rounded-lg px-2.5 py-1 transition"
                >
                  💡 NF-001002 (CloudData)
                </button>
                <button
                  onClick={() => {
                    const q = "Qual o valor total e produtos da nota NF-001003?";
                    setQuestion(q);
                    handleQuery(q);
                  }}
                  className="text-xs bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/20 rounded-lg px-2.5 py-1 transition"
                >
                  💡 NF-001003 (Papelaria)
                </button>
                <button
                  onClick={() => {
                    const q = "Qual o valor total e produtos da nota NF-001004?";
                    setQuestion(q);
                    handleQuery(q);
                  }}
                  className="text-xs bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 border border-purple-500/20 rounded-lg px-2.5 py-1 transition"
                >
                  💡 NF-001004 (Livraria DeepData)
                </button>
                <button
                  onClick={() => {
                    const q = "Qual é a capital da França?";
                    setQuestion(q);
                    handleQuery(q);
                  }}
                  className="text-xs bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/20 rounded-lg px-2.5 py-1 transition"
                  title="Testa a regra anti-alucinação estrita"
                >
                  🚫 Anti-Alucinação (Fora do Escopo)
                </button>
              </div>
            </div>

            {/* VISUALIZADOR DIDÁTICO DO PIPELINE */}
            {queryResult && (
              <div className="space-y-6 animate-fadeIn">
                {/* Stepper Visual do Pipeline */}
                <div className="glass-panel p-4 rounded-2xl">
                  <div className="flex items-center justify-between text-xs text-gray-400 mb-3 px-2 font-medium">
                    <span>ETAPAS DO PIPELINE DIDÁTICO EXECUTADAS:</span>
                    <span className="text-blue-400">Clique para inspecionar cada etapa</span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                    <button
                      onClick={() => setActiveStep(1)}
                      className={`p-3 rounded-xl border text-left transition flex flex-col justify-between h-24 ${
                        activeStep === 1
                          ? "bg-blue-600/20 border-blue-500 text-white"
                          : "bg-gray-800/40 border-white/5 text-gray-400 hover:border-white/20"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-blue-400">
                          Etapa 1
                        </span>
                        <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />
                      </div>
                      <div>
                        <div className="text-xs font-semibold text-gray-200">Tokenização</div>
                        <div className="text-[11px] text-gray-400">
                          {queryResult.pipeline.tokenization.token_count} tokens
                        </div>
                      </div>
                    </button>

                    <button
                      onClick={() => setActiveStep(2)}
                      className={`p-3 rounded-xl border text-left transition flex flex-col justify-between h-24 ${
                        activeStep === 2
                          ? "bg-indigo-600/20 border-indigo-500 text-white"
                          : "bg-gray-800/40 border-white/5 text-gray-400 hover:border-white/20"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400">
                          Etapa 2
                        </span>
                        <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
                      </div>
                      <div>
                        <div className="text-xs font-semibold text-gray-200">Embedding</div>
                        <div className="text-[11px] text-gray-400">
                          {queryResult.pipeline.embedding_dimension} Dimensões
                        </div>
                      </div>
                    </button>

                    <button
                      onClick={() => setActiveStep(3)}
                      className={`p-3 rounded-xl border text-left transition flex flex-col justify-between h-24 ${
                        activeStep === 3
                          ? "bg-purple-600/20 border-purple-500 text-white"
                          : "bg-gray-800/40 border-white/5 text-gray-400 hover:border-white/20"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-purple-400">
                          Etapa 3
                        </span>
                        <CheckCircle2 className="w-3.5 h-3.5 text-purple-400" />
                      </div>
                      <div>
                        <div className="text-xs font-semibold text-gray-200">Retrieval</div>
                        <div className="text-[11px] text-gray-400">
                          {queryResult.pipeline.candidates_found} candidatos
                        </div>
                      </div>
                    </button>

                    <button
                      onClick={() => setActiveStep(4)}
                      className={`p-3 rounded-xl border text-left transition flex flex-col justify-between h-24 ${
                        activeStep === 4
                          ? "bg-amber-600/20 border-amber-500 text-white"
                          : "bg-gray-800/40 border-white/5 text-gray-400 hover:border-white/20"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400">
                          Etapa 4
                        </span>
                        <CheckCircle2 className="w-3.5 h-3.5 text-amber-400" />
                      </div>
                      <div>
                        <div className="text-xs font-semibold text-gray-200">Prompt Augment</div>
                        <div className="text-[11px] text-gray-400">Contexto Fundido</div>
                      </div>
                    </button>

                    <button
                      onClick={() => setActiveStep(5)}
                      className={`p-3 rounded-xl border text-left transition flex flex-col justify-between h-24 ${
                        activeStep === 5
                          ? "bg-emerald-600/20 border-emerald-500 text-white"
                          : "bg-gray-800/40 border-white/5 text-gray-400 hover:border-white/20"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                          Etapa 5
                        </span>
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      </div>
                      <div>
                        <div className="text-xs font-semibold text-gray-200">Resposta LLM</div>
                        <div className="text-[11px] text-gray-400">OpenRouter AI</div>
                      </div>
                    </button>
                  </div>
                </div>

                {/* DETALHE DA ETAPA SELECIONADA */}
                {/* 1. Detalhe da Tokenização */}
                {activeStep === 1 && (
                  <div className="glass-panel p-6 rounded-2xl space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Cpu className="w-5 h-5 text-blue-400" />
                        <h3 className="font-semibold text-white">
                          Etapa 1: Tokenização Explícita da Pergunta (tiktoken)
                        </h3>
                      </div>
                      <span className="text-xs bg-blue-500/10 text-blue-300 border border-blue-500/20 px-2.5 py-1 rounded-full">
                        Codificação: cl100k_base
                      </span>
                    </div>
                    <p className="text-xs text-gray-400">
                      O modelo não lê palavras inteiras, mas sim "tokens" (pedaços de palavras ou caracteres). Abaixo estão os tokens exatos extraídos da sua pergunta:
                    </p>
                    <div className="p-4 rounded-xl bg-gray-900/80 border border-white/5">
                      <div className="text-xs text-gray-400 mb-2 font-mono">
                        Total: {queryResult.pipeline.tokenization.token_count} tokens
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {queryResult.pipeline.tokenization.tokens_visual.map((t, idx) => (
                          <div
                            key={idx}
                            className="token-chip"
                            title={`Token ID: ${t.id}`}
                          >
                            <span className="text-gray-400 text-[10px] mr-1">#{t.id}</span>
                            <span>"{t.piece}"</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* 2. Detalhe do Embedding */}
                {activeStep === 2 && (
                  <div className="glass-panel p-6 rounded-2xl space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Brain className="w-5 h-5 text-indigo-400" />
                        <h3 className="font-semibold text-white">
                          Etapa 2: Geração de Embedding Vetorial (FastEmbed)
                        </h3>
                      </div>
                      <span className="text-xs bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-2.5 py-1 rounded-full">
                        Modelo: BAAI/bge-small-en-v1.5
                      </span>
                    </div>
                    <p className="text-xs text-gray-400">
                      A pergunta foi transformada em um vetor matemático denso de{" "}
                      <strong className="text-indigo-300">{queryResult.pipeline.embedding_dimension} dimensões</strong>. Esse vetor captura o significado semântico para comparação geométrica.
                    </p>
                    <div className="p-4 rounded-xl bg-gray-900/80 border border-white/5 font-mono text-xs text-gray-300 space-y-2">
                      <div className="text-gray-400">Amostra didática das primeiras dimensões:</div>
                      <div className="grid grid-cols-2 sm:grid-cols-6 gap-2">
                        {queryResult.pipeline.embedding_preview.map((val, i) => (
                          <div key={i} className="p-2 bg-gray-800/80 rounded border border-white/5 text-center">
                            <span className="text-[10px] text-gray-500 block">Dim #{i + 1}</span>
                            <span className="text-indigo-400 font-bold">{val.toFixed(5)}</span>
                          </div>
                        ))}
                      </div>
                      <div className="text-[11px] text-gray-500 pt-2">
                        + 378 outras dimensões vetoriais calculadas pelo modelo local FastEmbed.
                      </div>
                    </div>
                  </div>
                )}

                {/* 3. Detalhe do Retrieval */}
                {activeStep === 3 && (
                  <div className="glass-panel p-6 rounded-2xl space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Search className="w-5 h-5 text-purple-400" />
                        <h3 className="font-semibold text-white">
                          Etapa 3: Retrieval Vetorial (Top-{topK} Candidatos)
                        </h3>
                      </div>
                      <span className="text-xs bg-purple-500/10 text-purple-300 border border-purple-500/20 px-2.5 py-1 rounded-full">
                        Cálculo: Similaridade de Cosseno
                      </span>
                    </div>

                    {queryResult.pipeline.candidates_found === 0 ? (
                      <div className="p-6 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center gap-3">
                        <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
                        <div>
                          <strong>Nenhum candidato relevante encontrado!</strong>
                          <p className="text-xs text-rose-300/80 mt-1">
                            A similaridade máxima ficou abaixo do corte de 0.60. O mecanismo anti-alucinação interceptou a resposta.
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {queryResult.pipeline.candidates.map((cand, idx) => (
                          <div
                            key={cand.chunk_id || cand.id || `candidate-${idx}`}
                            className="p-4 rounded-xl bg-gray-900/80 border border-white/5 hover:border-purple-500/30 transition space-y-2"
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="w-6 h-6 rounded-full bg-purple-500/20 text-purple-300 text-xs flex items-center justify-center font-bold">
                                  #{idx + 1}
                                </span>
                                <span className="text-xs font-semibold text-gray-300">
                                  Chunk #{cand.chunk_index} — Nota: {cand.invoice_number || "Geral"}
                                </span>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="text-xs text-gray-400">Score de Similaridade:</span>
                                <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-mono text-xs font-bold">
                                  {(cand.similarity * 100).toFixed(1)}% ({cand.similarity.toFixed(4)})
                                </span>
                              </div>
                            </div>
                            <pre className="text-xs text-gray-300 bg-gray-950/60 p-3 rounded-lg overflow-x-auto whitespace-pre-wrap font-sans">
                              {cand.content}
                            </pre>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* 4. Detalhe do Prompt Aumentado */}
                {activeStep === 4 && (
                  <div className="glass-panel p-6 rounded-2xl space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Layers className="w-5 h-5 text-amber-400" />
                        <h3 className="font-semibold text-white">
                          Etapa 4: Construção do Prompt Aumentado
                        </h3>
                      </div>
                      {queryResult.augmented_prompt && (
                        <button
                          onClick={copyPrompt}
                          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white bg-white/5 px-2.5 py-1 rounded-lg transition"
                        >
                          {promptCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                          {promptCopied ? "Copiado!" : "Copiar Prompt"}
                        </button>
                      )}
                    </div>
                    <p className="text-xs text-gray-400">
                      O "A" do RAG (Augmented) acontece aqui: as instruções de sistema, os candidatos recuperados e a pergunta do usuário são combinados em um único payload enviado ao modelo.
                    </p>
                    {queryResult.augmented_prompt ? (
                      <div className="p-4 rounded-xl bg-gray-950/90 border border-white/5 font-mono text-xs text-gray-300 max-h-96 overflow-y-auto whitespace-pre-wrap leading-relaxed">
                        {queryResult.augmented_prompt}
                      </div>
                    ) : (
                      <div className="p-4 rounded-xl bg-gray-900 border border-white/5 text-xs text-gray-400">
                        O prompt não foi gerado porque o limiar anti-alucinação barrou a requisição.
                      </div>
                    )}
                  </div>
                )}

                {/* 5. Resposta Final da LLM */}
                {activeStep === 5 && (
                  <div className="glass-panel p-6 rounded-2xl space-y-4 border-2 border-emerald-500/30">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Sparkles className="w-5 h-5 text-emerald-400" />
                        <h3 className="font-semibold text-white text-base">
                          Etapa 5: Resposta Gerada pelo LLM
                        </h3>
                      </div>
                      <span className="text-xs bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 px-2.5 py-1 rounded-full font-medium">
                        {queryResult.model_info}
                      </span>
                    </div>

                    <div className="p-5 rounded-xl bg-gradient-to-br from-gray-900/90 to-gray-950/90 border border-emerald-500/20 text-gray-100 text-sm leading-relaxed shadow-inner">
                      {queryResult.answer === "Sem dados disponiveis na base" ? (
                        <div className="flex items-center gap-3 text-amber-300">
                          <ShieldCheck className="w-5 h-5 text-amber-400 flex-shrink-0" />
                          <div>
                            <strong>Sem dados disponiveis na base</strong>
                            <p className="text-xs text-amber-400/80 mt-0.5">
                              Regra anti-alucinação acionada: A pergunta não possui correspondência factual suficiente nas notas fiscais cadastradas.
                            </p>
                          </div>
                        </div>
                      ) : (
                        <div className="whitespace-pre-wrap">{queryResult.answer}</div>
                      )}
                    </div>

                    {queryResult.token_usage?.total_tokens && (
                      <div className="flex items-center gap-4 text-xs text-gray-400 pt-1">
                        <span>
                          Tokens de Prompt:{" "}
                          <strong className="text-gray-300">
                            {queryResult.token_usage.prompt_tokens}
                          </strong>
                        </span>
                        <span>
                          Tokens de Resposta:{" "}
                          <strong className="text-gray-300">
                            {queryResult.token_usage.completion_tokens}
                          </strong>
                        </span>
                        <span>
                          Total:{" "}
                          <strong className="text-gray-300">
                            {queryResult.token_usage.total_tokens}
                          </strong>
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 2: PIPELINE DE INGESTÃO & CHUNKS */}
        {/* ========================================================================= */}
        {activeTab === "ingest" && (
          <div className="space-y-6">
            <div className="glass-panel p-5 rounded-2xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-l-4 border-l-indigo-500">
              <div className="space-y-1">
                <h2 className="text-base font-semibold text-white flex items-center gap-2">
                  <Layers className="w-4 h-4 text-indigo-400" />
                  Pipeline Didático de Ingestão
                </h2>
                <p className="text-sm text-gray-400">
                  Os documentos PDF passam por: Leitura/OCR → Estruturação Tabular → Chunking com Metadados → Tokenização tiktoken → Vetorização FastEmbed (384d) → Supabase PGVector.
                </p>
              </div>
              <button
                onClick={handleIngestDefaults}
                disabled={ingestingDefault}
                className="px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-50 text-white font-medium text-xs rounded-xl transition flex items-center gap-2 shadow-lg shadow-indigo-500/20 whitespace-nowrap"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${ingestingDefault ? "animate-spin" : ""}`} />
                {ingestingDefault ? "Ingerindo Notas..." : "Re-ingerir 4 Notas Fiscais de Teste"}
              </button>
            </div>

            {/* Upload de Novo Documento */}
            <div className="glass-panel p-6 rounded-2xl space-y-4">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Upload className="w-4 h-4 text-indigo-400" />
                Upload de Nova Nota Fiscal (PDF)
              </h3>
              <form onSubmit={handleUploadSubmit} className="flex flex-col sm:flex-row gap-3 items-center">
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="w-full sm:flex-1 text-xs text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-indigo-500/20 file:text-indigo-300 hover:file:bg-indigo-500/30 cursor-pointer"
                />
                <button
                  type="submit"
                  disabled={uploading || !uploadFile}
                  className="w-full sm:w-auto px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-xs rounded-xl transition flex items-center justify-center gap-2"
                >
                  {uploading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Processando PDF...
                    </>
                  ) : (
                    "Processar no Pipeline RAG"
                  )}
                </button>
              </form>
            </div>

            {/* Documentos Ingeridos e Detalhamento de Chunks */}
            <div className="glass-panel p-6 rounded-2xl space-y-4">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-400" />
                Visualizador de Chunks e Tokens dos Documentos
              </h3>
              <p className="text-xs text-gray-400">
                Clique em um documento para inspecionar como ele foi dividido em pedaços (chunking) e os tokens gerados.
              </p>

              {ingestLogs.length === 0 ? (
                <div className="p-8 text-center text-gray-400 text-xs border border-dashed border-white/10 rounded-xl space-y-3">
                  <p>Nenhum documento recém-processado exibido nesta sessão.</p>
                  <button
                    onClick={handleIngestDefaults}
                    className="px-4 py-2 bg-indigo-600/30 text-indigo-300 hover:bg-indigo-600/40 border border-indigo-500/30 rounded-xl transition text-xs"
                  >
                    Clique aqui para ingerir e visualizar as 4 notas didáticas
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  {ingestLogs.map((item: any, itemIdx: number) => {
                    const isExpanded = expandedDoc === item.doc_id;
                    return (
                      <div
                        key={item.doc_id || `log-${itemIdx}`}
                        className="rounded-xl border border-white/10 bg-gray-900/60 overflow-hidden transition"
                      >
                        <div
                          onClick={() => setExpandedDoc(isExpanded ? null : item.doc_id)}
                          className="p-4 flex items-center justify-between cursor-pointer hover:bg-white/5 transition"
                        >
                          <div className="flex items-center gap-3">
                            <span className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                              <FileText className="w-4 h-4" />
                            </span>
                            <div>
                              <div className="text-sm font-semibold text-gray-200">
                                {item.filename} — {item.parsed_fields?.numero_nota || "NF"}
                              </div>
                              <div className="text-xs text-gray-400">
                                Emitente: {item.parsed_fields?.fornecedor} | Total: R${" "}
                                {item.parsed_fields?.valor_total?.toLocaleString("pt-BR", {
                                  minimumFractionDigits: 2,
                                })}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="text-xs px-2.5 py-1 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20 font-medium">
                              {item.total_chunks} Chunks
                            </span>
                            {isExpanded ? (
                              <ChevronUp className="w-4 h-4 text-gray-400" />
                            ) : (
                              <ChevronDown className="w-4 h-4 text-gray-400" />
                            )}
                          </div>
                        </div>

                        {/* Detalhes Expansíveis dos Chunks */}
                        {isExpanded && (
                          <div className="p-4 border-t border-white/5 bg-gray-950/60 space-y-4">
                            <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                              Chunks Gerados com Metadados & Vetores:
                            </div>
                            <div className="space-y-3">
                              {item.chunks?.map((chunk: any, chunkIdx: number) => (
                                <div
                                  key={chunk.chunk_id || `chunk-${chunkIdx}`}
                                  className="p-3.5 rounded-lg bg-gray-900 border border-white/5 space-y-2 text-xs"
                                >
                                  <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                      <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-bold font-mono">
                                        Chunk #{chunk.chunk_index}
                                      </span>
                                      <span className="text-gray-400">Tipo: {chunk.chunk_type}</span>
                                    </div>
                                    <span className="text-gray-400 font-mono">
                                      {chunk.token_count} Tokens | {chunk.embedding_dimension} Dimensões
                                    </span>
                                  </div>
                                  <pre className="text-gray-300 bg-black/40 p-2.5 rounded whitespace-pre-wrap font-sans text-xs">
                                    {chunk.content}
                                  </pre>
                                  {chunk.tokens_visual && chunk.tokens_visual.length > 0 && (
                                    <div>
                                      <span className="text-[10px] text-gray-500 block mb-1">
                                        Tokens Individuais (Amostra):
                                      </span>
                                      <div className="flex flex-wrap gap-1">
                                        {chunk.tokens_visual.slice(0, 20).map((tv: any, i: number) => (
                                          <span key={i} className="token-chip text-[10px]">
                                            "{tv.piece}"
                                          </span>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 3: BASE DOCUMENTAL & VETORIAL */}
        {/* ========================================================================= */}
        {activeTab === "knowledge" && (
          <div className="space-y-6">
            {/* Informações da Conexão com Supabase */}
            <div className="glass-panel p-6 rounded-2xl space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Database className="w-5 h-5 text-indigo-400" />
                  <h3 className="font-semibold text-white">Status do Banco de Dados Vetorial</h3>
                </div>
                {health?.supabase_connected ? (
                  <span className="px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-semibold flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Supabase PGVector Ativo
                  </span>
                ) : (
                  <span className="px-3 py-1 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 text-xs font-semibold flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5" /> Armazenamento Espelhado Local Ativo
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-400 leading-relaxed">
                {health?.supabase_connected
                  ? "O banco remoto Supabase está conectado com a extensão PGVECTOR e tabelas criadas."
                  : "As credenciais do Supabase no .env foram validadas, porém as tabelas ainda precisam ser criadas executando o script supabase_schema.sql no SQL Editor do Supabase. Enquanto isso, o backend está usando o fallback local automático com dados pré-vetorizados."}
              </p>
            </div>

            {/* Lista de Documentos Cadastrados */}
            <div className="glass-panel p-6 rounded-2xl space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-white text-sm flex items-center gap-2">
                  <FileText className="w-4 h-4 text-blue-400" />
                  Documentos Fiscais no Banco ({documents.length})
                </h3>
                <button
                  onClick={fetchDocuments}
                  className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingDocs ? "animate-spin" : ""}`} />
                  Atualizar
                </button>
              </div>

              {documents.length === 0 ? (
                <p className="text-xs text-gray-500">Nenhum documento carregado.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {documents.map((doc, docIdx) => (
                    <div
                      key={doc.id || doc.invoice_number || `doc-${docIdx}`}
                      className="p-4 rounded-xl bg-gray-900/60 border border-white/5 hover:border-blue-500/30 transition space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-blue-400 font-mono">
                          {doc.invoice_number}
                        </span>
                        <span className="text-xs font-mono font-bold text-emerald-400">
                          R$ {doc.total_amount?.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                        </span>
                      </div>
                      <div className="text-xs text-gray-300 font-medium">{doc.supplier_name}</div>
                      <div className="text-[11px] text-gray-400 flex items-center justify-between">
                        <span>Destinatário: {doc.customer_name}</span>
                        <span>{doc.issue_date}</span>
                      </div>
                      <div className="pt-2">
                        <button
                          onClick={() => {
                            setActiveTab("query");
                            const q = `Quais produtos constam na nota fiscal ${doc.invoice_number}?`;
                            setQuestion(q);
                            handleQuery(q);
                          }}
                          className="w-full py-1.5 px-3 bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 rounded-lg text-xs font-medium border border-blue-500/20 transition flex items-center justify-center gap-1.5"
                        >
                          <Search className="w-3.5 h-3.5" /> Consultar esta Nota no Chat RAG
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
