import type {
  AdminAnalytics,
  AdminOverview,
  AdminUserItem,
  ChatResponse,
  Collection,
  ConversationDetail,
  ConversationSummary,
  DashboardSummary,
  DocumentDetail,
  DocumentSummary,
  DocumentUploadResult,
  EvaluationRun,
  KnowledgeSearchHit,
  SystemConfig,
  TokenResponse,
  User,
} from "@/lib/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000/api";

const TOKEN_STORAGE_KEY = "helpdesk_ai_token";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const headers = new Headers(init.headers || {});
  if (!headers.has("Content-Type") && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const errBody = await res.json();
      if (errBody?.detail) {
        detail = typeof errBody.detail === "string" ? errBody.detail : JSON.stringify(errBody.detail);
      }
    } catch {
      // ignore non-json error bodies
    }
    throw new Error(detail);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export const api = {
  // Auth
  login: (email: string, password: string) =>
    apiFetch<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (payload: {
    email: string;
    full_name: string;
    department: string;
    password: string;
  }) =>
    apiFetch<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  me: () => apiFetch<User>("/auth/me"),

  // Collections
  listCollections: () => apiFetch<Collection[]>("/collections"),
  createCollection: (payload: {
    name: string;
    slug?: string;
    description?: string;
    icon?: string;
    access_classification?: string;
  }) =>
    apiFetch<Collection>("/collections", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteCollection: (id: string) =>
    apiFetch<void>(`/collections/${id}`, { method: "DELETE" }),

  // Employee Dashboard & Knowledge
  getDashboardSummary: () => apiFetch<DashboardSummary>("/dashboard/summary"),
  listKnowledgeDocs: (category?: string, q?: string, collection_id?: string) => {
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (q) params.set("q", q);
    if (collection_id) params.set("collection_id", collection_id);
    const qs = params.toString();
    return apiFetch<DocumentSummary[]>(`/knowledge/documents${qs ? `?${qs}` : ""}`);
  },
  searchKnowledge: (q: string, category?: string, collection_id?: string) => {
    const params = new URLSearchParams({ q });
    if (category) params.set("category", category);
    if (collection_id) params.set("collection_id", collection_id);
    return apiFetch<KnowledgeSearchHit[]>(`/knowledge/search?${params.toString()}`);
  },
  getKnowledgeDocDetail: (id: string) => apiFetch<DocumentDetail>(`/knowledge/documents/${id}`),

  // Chat & Conversations
  listConversations: (q?: string) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    const qs = params.toString();
    return apiFetch<ConversationSummary[]>(`/conversations${qs ? `?${qs}` : ""}`);
  },
  getConversation: (id: string) => apiFetch<ConversationDetail>(`/conversations/${id}`),
  deleteConversation: (id: string) =>
    apiFetch<void>(`/conversations/${id}`, { method: "DELETE" }),
  sendFeedback: (message_id: string, rating: "helpful" | "not_helpful", comment?: string) =>
    apiFetch("/feedback", {
      method: "POST",
      body: JSON.stringify({ message_id, rating, comment }),
    }),

  // Admin Documents
  listAdminDocuments: () => apiFetch<DocumentSummary[]>("/documents"),
  getAdminDocumentDetail: (id: string) => apiFetch<DocumentDetail>(`/documents/${id}`),
  reprocessDocument: (id: string) =>
    apiFetch<DocumentSummary>(`/documents/${id}/reprocess`, { method: "POST" }),
  deleteDocument: (id: string) =>
    apiFetch<void>(`/documents/${id}`, { method: "DELETE" }),
  updateDocument: (
    id: string,
    payload: {
      title?: string;
      category?: string;
      department?: string;
      access_classification?: string;
    }
  ) =>
    apiFetch<DocumentSummary>(`/documents/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  // Admin Overview, Analytics, Users, Config, Evaluation
  getAdminOverview: () => apiFetch<AdminOverview>("/admin/overview"),
  getAdminAnalytics: () => apiFetch<AdminAnalytics>("/admin/analytics"),
  getAdminUsers: () => apiFetch<AdminUserItem[]>("/admin/users"),
  updateAdminUser: (
    id: string,
    payload: { role?: string; is_active?: boolean; department?: string }
  ) =>
    apiFetch<AdminUserItem>(`/admin/users/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  getSystemConfig: () => apiFetch<SystemConfig>("/admin/config"),
  listEvaluations: () => apiFetch<EvaluationRun[]>("/admin/evaluation/results"),
  runEvaluation: (modes: string[], k_value = 5) =>
    apiFetch<EvaluationRun[]>("/admin/evaluation/run", {
      method: "POST",
      body: JSON.stringify({ modes, k_value, run_llm_judge: false }),
    }),
};

export async function streamChat(
  payload: {
    question: string;
    conversation_id?: string | null;
    category_filter?: string | null;
    collection_id?: string | null;
    retrieval_mode?: "semantic" | "hybrid" | "hybrid_rerank";
  },
  callbacks: {
    onToken: (token: string) => void;
    onDone: (res: ChatResponse) => void;
    onError: (detail: string) => void;
  }
): Promise<void> {
  const token = getStoredToken();
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok || !res.body) {
    let detail = `Chat request failed (${res.status})`;
    try {
      const err = await res.json();
      if (err?.detail) detail = err.detail;
    } catch {
      // ignore
    }
    callbacks.onError(detail);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() || "";

    for (const block of lines) {
      const dataLine = block
        .split("\n")
        .find((l) => l.startsWith("data: "));
      if (!dataLine) continue;
      try {
        const event = JSON.parse(dataLine.slice(6));
        if (event.type === "token" && event.content) {
          callbacks.onToken(event.content);
        } else if (event.type === "done" && event.payload) {
          callbacks.onDone(event.payload as ChatResponse);
        } else if (event.type === "error") {
          callbacks.onError(event.detail || "Generation error.");
        }
      } catch {
        // ignore malformed chunk
      }
    }
  }
}

export function uploadDocumentsWithProgress(
  files: File[],
  metadata: {
    category: string;
    department: string;
    access_classification: string;
    title?: string;
    collection_id?: string;
  },
  onProgress: (percent: number) => void
): Promise<DocumentUploadResult[]> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    form.append("category", metadata.category);
    form.append("department", metadata.department);
    form.append("access_classification", metadata.access_classification);
    if (metadata.title) form.append("title", metadata.title);
    if (metadata.collection_id) form.append("collection_id", metadata.collection_id);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/documents/upload`);
    const token = getStoredToken();
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.onprogress = (ev) => {
      if (ev.lengthComputable) {
        onProgress(Math.round((ev.loaded / ev.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as DocumentUploadResult[]);
        } catch {
          reject(new Error("Invalid upload response."));
        }
      } else {
        try {
          const err = JSON.parse(xhr.responseText);
          reject(new Error(err?.detail || `Upload failed (${xhr.status})`));
        } catch {
          reject(new Error(`Upload failed (${xhr.status})`));
        }
      }
    };
    xhr.onerror = () => reject(new Error("Network error while uploading documents."));
    xhr.send(form);
  });
}

