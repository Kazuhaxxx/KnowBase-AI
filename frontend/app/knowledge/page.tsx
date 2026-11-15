"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { BookOpen, FileText, Plus, Search, Trash2, Upload, X } from "lucide-react";
import type { Collection, DocumentDetail, DocumentSummary, KnowledgeSearchHit } from "@/lib/types";
import { formatBytes, formatDateTime } from "@/lib/utils";
import { api, uploadDocumentsWithProgress } from "@/services/api";
import { Badge, Button, Card, Input } from "@/components/ui/primitives";

const CATEGORIES = [
  "Company Policies",
  "Standard Operating Procedures (SOPs)",
  "HR & Benefits",
  "Product Manuals",
  "Technical Documentation",
  "Training & Onboarding",
  "Legal & Compliance",
  "General Knowledge",
  "Microsoft 365",
  "VPN",
  "Network",
  "Hardware",
  "Software",
  "Account and Access",
  "IT Policies",
  "Troubleshooting",
  "General IT Support",
];

function KnowledgeExplorerInner() {
  const params = useSearchParams();
  const initialDocId = params.get("docId");

  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState("");
  const [hits, setHits] = useState<KnowledgeSearchHit[] | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [category, setCategory] = useState("");
  const [selectedDoc, setSelectedDoc] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);

  const [showUpload, setShowUpload] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [uploadCategory, setUploadCategory] = useState("General Knowledge");
  const [uploadCollectionId, setUploadCollectionId] = useState("");
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const [uploadErr, setUploadErr] = useState<string | null>(null);

  useEffect(() => {
    api.listCollections().then(setCollections).catch(() => {});
  }, []);

  const loadDocs = async (cat?: string, collId?: string) => {
    setLoading(true);
    try {
      const list = await api.listKnowledgeDocs(cat || undefined, undefined, collId || undefined);
      setDocs(list);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocs(category, selectedCollectionId);
  }, [category, selectedCollectionId]);

  useEffect(() => {
    if (initialDocId) {
      api.getKnowledgeDocDetail(initialDocId).then(setSelectedDoc).catch(() => {});
    }
  }, [initialDocId]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      setHits(null);
      return;
    }
    const res = await api.searchKnowledge(
      searchQuery.trim(),
      category || undefined,
      selectedCollectionId || undefined
    );
    setHits(res);
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (files.length === 0) return;
    setUploadErr(null);
    setUploadMsg(null);
    setUploadProgress(0);
    try {
      const results = await uploadDocumentsWithProgress(
        files,
        {
          category: uploadCategory,
          department: "General",
          access_classification: "employee",
          collection_id: uploadCollectionId || undefined,
        },
        setUploadProgress
      );
      setUploadMsg(results.map((r) => `${r.document.original_filename}: ${r.message}`).join(" | "));
      setFiles([]);
      await loadDocs(category, selectedCollectionId);
    } catch (err) {
      setUploadErr(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploadProgress(null);
    }
  };

  const handleDelete = async (id: string) => {
    await api.deleteDocument(id);
    setDocs((prev) => prev.filter((d) => d.id !== id));
  };

  const openDocument = async (id: string) => {
    const detail = await api.getKnowledgeDocDetail(id);
    setSelectedDoc(detail);
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-4 sm:p-6 lg:p-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Knowledge Base & Documents</h1>
          <p className="text-xs text-muted-foreground">
            Explore verified company knowledge, procedures, and manuals, or upload new documentation.
          </p>
        </div>
        <Button size="sm" onClick={() => setShowUpload((v) => !v)}>
          <Plus className="h-4 w-4" />
          {showUpload ? "Close Upload" : "Upload Document"}
        </Button>
      </div>

      {showUpload && (
        <Card className="p-4">
          <form onSubmit={handleUpload} className="space-y-3">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <input
                type="file"
                multiple
                accept=".pdf,.docx,.txt,.md"
                onChange={(e) => setFiles(Array.from(e.target.files || []))}
                className="flex-1 text-xs file:mr-3 file:rounded-md file:border-0 file:bg-secondary file:px-3 file:py-1.5 file:text-xs file:font-medium"
              />
              <select
                value={uploadCollectionId}
                onChange={(e) => setUploadCollectionId(e.target.value)}
                className="h-9 rounded-md border border-input bg-background px-3 text-xs"
              >
                <option value="">Default Collection</option>
                {collections.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
              <select
                value={uploadCategory}
                onChange={(e) => setUploadCategory(e.target.value)}
                className="h-9 rounded-md border border-input bg-background px-3 text-xs"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              <Button type="submit" size="sm" disabled={files.length === 0 || uploadProgress !== null}>
                <Upload className="h-3.5 w-3.5" />
                {uploadProgress !== null ? `Uploading ${uploadProgress}%` : "Ingest"}
              </Button>
            </div>
            {uploadMsg && (
              <p className="text-xs text-emerald-600 dark:text-emerald-400">{uploadMsg}</p>
            )}
            {uploadErr && <p className="text-xs text-rose-500">{uploadErr}</p>}
          </form>
        </Card>
      )}

      {/* Search & Filter */}
      <Card className="p-4">
        <form onSubmit={handleSearch} className="flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                if (!e.target.value.trim()) setHits(null);
              }}
              placeholder="Search across all knowledge documents, policies, SOPs, and guides..."
              className="pl-9"
            />
          </div>
          <select
            value={selectedCollectionId}
            onChange={(e) => setSelectedCollectionId(e.target.value)}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          >
            <option value="">All Collections</option>
            {collections.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.document_count})
              </option>
            ))}
          </select>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          >
            <option value="">All Categories</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <Button type="submit">Search</Button>
          {hits && (
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setSearchQuery("");
                setHits(null);
              }}
            >
              Clear
            </Button>
          )}
        </form>
      </Card>

      {/* Hybrid Search Results */}
      {hits ? (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold">Search Matches ({hits.length})</h2>
          {hits.length === 0 ? (
            <Card className="p-6 text-center text-xs text-muted-foreground">
              No documentation passages matched your query.
            </Card>
          ) : (
            hits.map((hit) => (
              <Card key={hit.chunk_id} className="p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-primary" />
                    <button
                      type="button"
                      onClick={() => openDocument(hit.document_id)}
                      className="text-sm font-semibold hover:text-primary hover:underline"
                    >
                      {hit.document_title}
                    </button>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{hit.category}</Badge>
                    <Badge variant="default">Score {(hit.score * 100).toFixed(0)}%</Badge>
                  </div>
                </div>
                <p className="mt-2 rounded bg-muted/40 p-3 font-mono text-xs leading-relaxed">
                  {hit.excerpt}
                </p>
              </Card>
            ))
          )}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading documents...</p>
          ) : (
            docs.map((doc) => (
              <Card
                key={doc.id}
                className="flex flex-col justify-between p-4 transition-colors hover:border-primary/40"
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <Badge variant="outline">{doc.category}</Badge>
                    <button
                      type="button"
                      onClick={() => handleDelete(doc.id)}
                      className="rounded p-1 text-muted-foreground hover:text-rose-500"
                      title="Delete document"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <h3 className="mt-3 text-sm font-semibold">{doc.title}</h3>
                  <p className="mt-1 text-xs text-muted-foreground">{doc.original_filename}</p>
                </div>

                <div className="mt-4 flex items-center justify-between border-t pt-3 text-xs text-muted-foreground">
                  <span>
                    {doc.chunk_count} chunks • {formatBytes(doc.file_size_bytes)}
                  </span>
                  <Button size="sm" variant="ghost" onClick={() => openDocument(doc.id)}>
                    <BookOpen className="h-3.5 w-3.5" />
                    Read
                  </Button>
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {/* Document Reader Modal */}
      {selectedDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-black/50" onClick={() => setSelectedDoc(null)} />
          <Card className="relative z-10 flex max-h-[85vh] w-full max-w-3xl flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b px-5 py-4">
              <div>
                <h3 className="text-base font-semibold">{selectedDoc.title}</h3>
                <p className="text-xs text-muted-foreground">
                  {selectedDoc.original_filename} • v{selectedDoc.version} • Updated{" "}
                  {formatDateTime(selectedDoc.last_processed_at)}
                </p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setSelectedDoc(null)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex-1 space-y-4 overflow-y-auto p-5">
              {selectedDoc.chunks.map((chunk) => (
                <div key={chunk.id} className="rounded-md border bg-muted/20 p-4">
                  <div className="mb-2 flex items-center justify-between text-xs text-muted-foreground">
                    <span>
                      Chunk #{chunk.chunk_index}
                      {chunk.section_heading ? ` — ${chunk.section_heading}` : ""}
                    </span>
                    <span>
                      {chunk.page_number ? `Page ${chunk.page_number}` : "Page N/A"}
                    </span>
                  </div>
                  <p className="whitespace-pre-wrap text-sm leading-relaxed">
                    {chunk.cleaned_content}
                  </p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

export default function KnowledgeExplorerPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">Loading...</div>}>
      <KnowledgeExplorerInner />
    </Suspense>
  );
}
