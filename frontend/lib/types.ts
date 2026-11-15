export type UserRole = "employee" | "it_staff" | "admin";

export interface User {
  id: string;
  email: string;
  full_name: string;
  department: string;
  role: UserRole;
  is_active: boolean;
  allowed_classifications: string[];
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Collection {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  icon: string;
  access_classification: string;
  document_count: number;
  created_at: string;
  updated_at?: string | null;
}

export interface DocumentSummary {
  id: string;
  title: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  file_hash: string;
  category: string;
  department: string;
  access_classification: "public" | "employee" | "it_only" | "restricted";
  collection_id?: string | null;
  version: number;
  processing_status: "pending" | "processing" | "indexed" | "failed";
  error_message?: string | null;
  page_count?: number | null;
  chunk_count: number;
  created_at: string;
  last_processed_at?: string | null;
}

export interface DocumentChunk {
  id: string;
  chunk_index: number;
  content: string;
  cleaned_content: string;
  page_number?: number | null;
  section_heading?: string | null;
  token_count: number;
  char_count: number;
  embedding_model: string;
  embedding_dim: number;
  metadata_json: Record<string, unknown>;
}

export interface DocumentDetail extends DocumentSummary {
  extracted_preview?: string | null;
  chunks: DocumentChunk[];
}

export interface DocumentUploadResult {
  document: DocumentSummary;
  duplicate_detected: boolean;
  replaced_previous_version: boolean;
  message: string;
}

export interface KnowledgeSearchHit {
  document_id: string;
  document_title: string;
  original_filename: string;
  category: string;
  department: string;
  access_classification: string;
  page_number?: number | null;
  chunk_id: string;
  chunk_index: number;
  excerpt: string;
  score: number;
}

export interface Citation {
  id: string;
  document_id?: string | null;
  chunk_id?: string | null;
  document_title: string;
  original_filename: string;
  page_number?: number | null;
  chunk_index?: number | null;
  passage_excerpt: string;
  relevance_score: number;
  rank_order: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  rewritten_query?: string | null;
  confidence_score?: number | null;
  evidence_sufficient?: boolean | null;
  provider_used?: string | null;
  model_used?: string | null;
  retrieval_latency_ms?: number | null;
  generation_latency_ms?: number | null;
  total_latency_ms?: number | null;
  citations: Citation[];
  created_at: string;
}

export interface ChatResponse {
  conversation_id: string;
  conversation_title: string;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message_preview?: string | null;
}

export interface ConversationDetail {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

export interface DashboardSummary {
  user: { full_name: string; role: UserRole; department: string };
  usage: { conversations: number; questions_asked: number; accessible_articles: number };
  recent_conversations: { id: string; title: string; updated_at: string }[];
  recently_updated_articles: {
    id: string;
    title: string;
    category: string;
    access_classification: string;
    last_processed_at?: string | null;
  }[];
  popular_topics: { topic: string; prompt: string }[];
}

export interface AdminOverview {
  total_documents: number;
  indexed_documents: number;
  failed_documents: number;
  pending_documents: number;
  total_chunks: number;
  total_conversations: number;
  total_questions: number;
  helpful_feedback: number;
  not_helpful_feedback: number;
  top_categories: { category: string; count: number }[];
  recent_documents: {
    id: string;
    title: string;
    category: string;
    status: string;
    classification: string;
    chunk_count: number;
    created_at: string;
  }[];
}

export interface AdminAnalytics {
  total_questions: number;
  total_conversations: number;
  avg_total_latency_ms: number;
  avg_retrieval_latency_ms: number;
  avg_generation_latency_ms: number;
  evidence_sufficiency_rate: number;
  failed_retrieval_count: number;
  helpful_feedback: number;
  not_helpful_feedback: number;
  frequently_retrieved_documents: { document_id: string; title: string; count: number }[];
  category_breakdown: { category: string; count: number }[];
  latency_trend: {
    index: number;
    retrieval_ms: number;
    generation_ms: number;
    total_ms: number;
    sufficient: boolean;
  }[];
}

export interface SystemConfig {
  ai_execution_mode: "local" | "cloud";
  active_provider: string;
  active_model: string;
  ollama_base_url: string;
  ollama_available: boolean;
  ollama_models_installed: string[];
  gemini_configured: boolean;
  gemini_model: string;
  embedding_model: string;
  embedding_dim: number;
  reranker_model: string;
  enable_reranking: boolean;
  enable_query_rewriting: boolean;
  chunk_size: number;
  chunk_overlap: number;
  rrf_k: number;
  semantic_weight: number;
  bm25_weight: number;
  retrieval_top_n_final: number;
  database_status: { connected: boolean; dialect: string; pgvector_enabled: boolean };
  security_notice: string;
}

export interface AdminUserItem {
  id: string;
  email: string;
  full_name: string;
  department: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface EvaluationRun {
  id: string;
  run_name: string;
  retrieval_mode: string;
  dataset_name: string;
  question_count: number;
  k_value: number;
  recall_at_k: number;
  precision_at_k: number;
  mrr: number;
  context_relevance: number;
  faithfulness?: number | null;
  answer_relevance?: number | null;
  citation_correctness?: number | null;
  llm_evaluated: boolean;
  metrics_by_category: Record<
    string,
    {
      count: number;
      recall_at_k: number;
      precision_at_k: number;
      mrr: number;
      context_relevance: number;
    }
  >;
  notes: string;
  created_at: string;
}

