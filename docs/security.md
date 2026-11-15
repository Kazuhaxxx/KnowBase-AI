# Security Architecture & Demonstration Limitations

## Implemented Controls
1. **Authentication & Password Storage**: Argon2id password hashing via `argon2-cffi`; signed HS256 JWT bearer tokens with expiration.
2. **Server-Side RBAC & Document Isolation**:
   - Roles (`employee`, `it_staff`, `admin`) map strictly on the server to permitted `access_classification` values (`public`, `employee`, `it_only`, `restricted`).
   - Retrieval queries filter `Document.access_classification.in_(allowed_classifications)` inside SQL *before* vector scoring, BM25 scoring, reranking, or LLM prompting.
   - Client requests cannot override or widen access scope.
3. **Conversation Isolation**: Users can only read or delete conversations owned by their authenticated `user_id`.
4. **Prompt Injection Defense**:
   - Ingestion inspects chunks for override phrases (`ignore all previous instructions`, etc.) and flags `untrusted_instruction_flagged` in metadata.
   - All retrieved text is wrapped in `<retrieved_document>` XML tags and treated strictly as untrusted data by the system prompt.
5. **Upload Validation**: Extension allowlist (`.pdf`, `.docx`, `.txt`, `.md`), file size cap (`MAX_UPLOAD_SIZE_MB`), PDF/DOCX magic-byte verification, path-traversal sanitization, and zero execution of uploaded bytes.
6. **Non-Sensitive Telemetry & Secret Hygiene**:
   - `query_telemetry` records latency, category, sufficiency boolean, and cited document IDs only — never prompt text, user IDs, or chunk text.
   - `GEMINI_API_KEY` and `JWT_SECRET_KEY` reside strictly in backend environment variables and are never returned to the frontend.
7. **Rate Limiting**: `slowapi` limits auth, chat, and general endpoints.

## Demonstration Environment Limitations
- This repository ships with synthetic demonstration accounts and fictional NovaTech Global documentation.
- It is **not** enterprise-certified or production-ready out of the box. Before production deployment, teams must:
  - Replace `JWT_SECRET_KEY` and demo credentials, and integrate enterprise SSO (OIDC/SAML).
  - Serve traffic strictly behind TLS/HTTPS with reverse-proxy headers and WAF rules.
  - Perform an independent security audit, penetration test, and compliance review (SOC 2 / ISO 27001 / GDPR) for Cloud AI data egress if `AI_EXECUTION_MODE=cloud` is enabled.

