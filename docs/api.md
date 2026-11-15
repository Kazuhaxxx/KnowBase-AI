# REST API Reference — KnowBase AI

Interactive OpenAPI documentation is automatically served by FastAPI at `/docs` and `/redoc`.

## Endpoint Summary

### Health
- `GET /api/health` — Database, pgvector, AI mode, and Ollama availability status.

### Authentication
- `POST /api/auth/register` — Register an employee account (rate-limited).
- `POST /api/auth/login` — Authenticate and receive a JWT bearer token.
- `GET /api/auth/me` — Retrieve authenticated profile and permitted document classifications.

### Collections (Knowledge Hubs)
- `GET /api/collections` — List accessible collections with live document counts.
- `GET /api/collections/{id}` — Retrieve details and document count for a single collection.
- `POST /api/collections` — Create a new collection (`admin` role required).
- `PATCH /api/collections/{id}` — Update a collection's name, description, icon, or classification (`admin` role required).
- `DELETE /api/collections/{id}` — Delete a collection (`admin` role required).

### Knowledge Explorer (Authenticated, RBAC-Filtered)
- `GET /api/knowledge/documents` — Browse accessible indexed documents (`category`, `collection_id`, `q`).
- `GET /api/knowledge/search` — Hybrid retrieval search over authorized documents (`q`, `category`, `collection_id`, `limit`).
- `GET /api/knowledge/documents/{id}` — Inspect an authorized document and its chunks.

### AI Knowledge Assistant Chat & History (Authenticated, User-Scoped)
- `POST /api/chat` — Synchronous grounded RAG chat turn returning verified citations, latencies, and collection filter support.
- `POST /api/chat/stream` — Server-Sent Events (SSE) streaming chat response + final citation payload.
- `GET /api/conversations` — List user's personal conversations (supports search via `?q=...`).
- `GET /api/conversations/{id}` — Load messages and citations for a personal conversation.
- `DELETE /api/conversations/{id}` — Delete a personal conversation.
- `GET /api/dashboard/summary` — Portal usage summary and recently updated articles.
- `POST /api/feedback` — Submit `helpful` or `not_helpful` rating for an assistant message.

### Administration & Knowledge Management (`admin` Role Required)
- `POST /api/documents/upload` — Upload one or multiple documents with category and collection assignment (multipart form-data).
- `GET /api/documents` — List all documents across all classifications, collections, and statuses.
- `GET /api/documents/{id}` — Inspect document metadata, preview text, and indexed chunks.
- `PATCH /api/documents/{id}` — Update title, category, department, collection, or access classification.
- `POST /api/documents/{id}/reprocess` — Re-extract, re-chunk, and re-embed document.
- `DELETE /api/documents/{id}` — Delete document, chunks, and stored file.
- `GET /api/admin/overview` — Document, conversation, and feedback summary metrics.
- `GET /api/admin/analytics` — Non-sensitive latency, sufficiency, and citation analytics.
- `GET /api/admin/users` — List registered users.
- `PATCH /api/admin/users/{id}` — Update user role, department, or active status.
- `GET /api/admin/config` — Active AI execution mode, models, and RAG parameters (no secrets).
- `POST /api/admin/evaluation/run` — Execute benchmark evaluation across retrieval modes.
- `GET /api/admin/evaluation/results` — List stored benchmark evaluation runs.
