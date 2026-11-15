# RAG Pipeline Design — KnowBase AI

## 1. Ingestion & Structure-Aware Chunking
- **PDF (`PyMuPDF`)**: Extracts text page-by-page while recording `page_number` and inferring section headings.
- **DOCX (`python-docx`)**: Preserves paragraph heading context and serializes troubleshooting tables into pipe-delimited rows.
- **TXT / Markdown**: Splits Markdown along `#`–`###` headings so procedural sections remain cohesive.
- **Chunking**: Configurable `CHUNK_SIZE` (default 650 chars) and `CHUNK_OVERLAP` (default 120 chars), keeping short consecutive numbered steps intact and attaching full document metadata to every chunk.
- **Deduplication & Versioning**: SHA-256 hash detects exact duplicates; uploading an updated file with the same filename atomically replaces prior chunks and increments `version`.

## 2. Why Hybrid Retrieval (Semantic + BM25 + RRF)?
Pure semantic vector search captures paraphrases ("my mail cache is broken" -> "corrupted OST file") but often struggles on exact IT identifiers such as error codes (`0x8004de40`, `VPN-403`, `0x80070005`), hostnames (`vpn-gw.novatech-demo.internal`), or CLI flags (`onedrive.exe /reset`).

KnowBase AI combines:
1. **Semantic Retrieval**: Cosine similarity via `pgvector` (`all-MiniLM-L6-v2`, 384 dimensions).
2. **BM25 Keyword Retrieval**: `BM25Plus` with a custom tokenizer that preserves hex error codes, hyphenated flags, and domain names.
3. **Reciprocal Rank Fusion (RRF)**:
   $$\text{RRF}(d) = \frac{w_{\text{sem}}}{k + \text{rank}_{\text{sem}}(d)} + \frac{w_{\text{bm25}}}{k + \text{rank}_{\text{bm25}}(d)}$$
   with default `k=60`, `w_sem=0.6`, `w_bm25=0.4`.

## 3. Why Cross-Encoder Reranking?
Bi-encoder embeddings encode queries and chunks independently, trading off fine-grained token-level interaction for speed. After Hybrid Retrieval fetches the top candidate pool, `CrossEncoder` (`cross-encoder/ms-marco-MiniLM-L-6-v2`) jointly attends across `(query, document_title + chunk_text)` pairs to score exact procedural relevance before context construction. If cross-encoder weights are unavailable, the pipeline logs a warning and falls back to RRF ordering.

## 4. Evidence Sufficiency & Citation Validation
KnowBase AI does **not** rely on LLM self-reported confidence:
1. **Pre-Generation Guard (`assess_evidence_sufficiency`)**: Evaluates top retrieval/rerank score against `EVIDENCE_MIN_SCORE` and query-to-context token coverage against `EVIDENCE_MIN_TERM_COVERAGE`. If insufficient, the system immediately returns the abstention fallback without invoking the LLM.
2. **Post-Generation Validator (`validate_and_select_citations`)**: Verifies every `[Source N]` reference maps to an actual chunk passed in the prompt context, stripping any fabricated indices.

