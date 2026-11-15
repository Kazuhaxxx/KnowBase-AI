"use client";

import React, { useEffect, useState } from "react";
import { Eye, RefreshCw, Trash2, Upload, X } from "lucide-react";
import type { DocumentDetail, DocumentSummary } from "@/lib/types";
import { formatBytes, formatDateTime } from "@/lib/utils";
import { api, uploadDocumentsWithProgress } from "@/services/api";
import { Badge, Button, Card, Input } from "@/components/ui/primitives";

const CATEGORIES = [
  "Network",
  "Hardware",
  "Software",
  "Microsoft 365",
  "Account and Access",
  "VPN",
  "IT Policies",
  "Troubleshooting",
  "General IT Support",
];

const CLASSIFICATIONS = ["public", "employee", "it_only", "restricted"];

export default function AdminDocumentsPage() {
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [files, setFiles] = useState<File[]>([]);
  const [category, setCategory] = useState("General IT Support");
  const [department, setDepartment] = useState("IT Operations");
  const [classification, setClassification] = useState("employee");
  const [title, setTitle] = useState("");
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [inspectedDoc, setInspectedDoc] = useState<DocumentDetail | null>(null);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const data = await api.listAdminDocuments();
      setDocs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (files.length === 0) return;
    setError(null);
    setStatusMessage(null);
    setUploadProgress(0);
    try {
      const results = await uploadDocumentsWithProgress(
        files,
        {
          category,
          department,
          access_classification: classification,
          title: title.trim() || undefined,
        },
        setUploadProgress
      );
      setStatusMessage(results.map((r) => `${r.document.original_filename}: ${r.message}`).join(" | "));
      setFiles([]);
      setTitle("");
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploadProgress(null);
    }
  };

  const handleInspect = async (id: string) => {
    const detail = await api.getAdminDocumentDetail(id);
    setInspectedDoc(detail);
  };

  const handleReprocess = async (id: string) => {
    await api.reprocessDocument(id);
    await loadDocuments();
  };

  const handleDelete = async (id: string) => {
    await api.deleteDocument(id);
    setDocs((prev) => prev.filter((d) => d.id !== id));
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Knowledge Base Management</h1>
        <p className="text-xs text-muted-foreground">
          Upload PDF, DOCX, TXT, or Markdown documentation, manage access classifications, and inspect indexed chunks.
        </p>
      </div>

      {/* Upload Form */}
      <Card className="p-5">
        <h2 className="mb-4 text-sm font-semibold">Upload & Ingest Documents</h2>
        <form onSubmit={handleUpload} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-1">
              <label className="text-xs font-medium">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium">Access Classification</label>
              <select
                value={classification}
                onChange={(e) => setClassification(e.target.value)}
                className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                {CLASSIFICATIONS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium">Department</label>
              <Input
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                placeholder="IT Operations"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium">Custom Title (Single File)</label>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Optional override"
              />
            </div>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <input
              type="file"
              multiple
              accept=".pdf,.docx,.txt,.md"
              onChange={(e) => setFiles(Array.from(e.target.files || []))}
              className="flex-1 text-xs file:mr-3 file:rounded-md file:border-0 file:bg-secondary file:px-3 file:py-1.5 file:text-xs file:font-medium"
            />
            <Button type="submit" disabled={files.length === 0 || uploadProgress !== null}>
              <Upload className="h-4 w-4" />
              {uploadProgress !== null ? `Uploading ${uploadProgress}%` : `Upload (${files.length})`}
            </Button>
          </div>

          {uploadProgress !== null && (
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full bg-primary transition-all"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          )}

          {statusMessage && (
            <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-700 dark:text-emerald-400">
              {statusMessage}
            </div>
          )}
          {error && (
            <div className="rounded-md border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-600 dark:text-rose-400">
              {error}
            </div>
          )}
        </form>
      </Card>

      {/* Documents Table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b bg-muted/40 text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-semibold">Document</th>
                <th className="px-4 py-3 font-semibold">Category</th>
                <th className="px-4 py-3 font-semibold">Access</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold">Chunks / Ver</th>
                <th className="px-4 py-3 font-semibold">Processed</th>
                <th className="px-4 py-3 text-right font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-muted-foreground">
                    Loading documents...
                  </td>
                </tr>
              ) : (
                docs.map((doc) => (
                  <tr key={doc.id} className="hover:bg-muted/20">
                    <td className="px-4 py-3">
                      <p className="font-semibold text-foreground">{doc.title}</p>
                      <p className="text-[11px] text-muted-foreground">
                        {doc.original_filename} • {formatBytes(doc.file_size_bytes)}
                      </p>
                    </td>
                    <td className="px-4 py-3">{doc.category}</td>
                    <td className="px-4 py-3">
                      <Badge
                        variant={
                          doc.access_classification === "restricted"
                            ? "danger"
                            : doc.access_classification === "it_only"
                            ? "warning"
                            : "outline"
                        }
                      >
                        {doc.access_classification}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={doc.processing_status === "indexed" ? "success" : "danger"}>
                        {doc.processing_status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      {doc.chunk_count} chunks • v{doc.version}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {formatDateTime(doc.last_processed_at)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleInspect(doc.id)}
                          title="Inspect preview & chunks"
                        >
                          <Eye className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleReprocess(doc.id)}
                          title="Reprocess chunks & embeddings"
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(doc.id)}
                          title="Delete document"
                        >
                          <Trash2 className="h-3.5 w-3.5 text-rose-500" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Chunk Inspector Modal */}
      {inspectedDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-black/50" onClick={() => setInspectedDoc(null)} />
          <Card className="relative z-10 flex max-h-[88vh] w-full max-w-4xl flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b px-5 py-4">
              <div>
                <h3 className="text-base font-semibold">{inspectedDoc.title}</h3>
                <p className="text-xs text-muted-foreground">
                  SHA-256: {inspectedDoc.file_hash.slice(0, 16)}... • {inspectedDoc.chunk_count} chunks
                </p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setInspectedDoc(null)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex-1 space-y-4 overflow-y-auto p-5">
              {inspectedDoc.extracted_preview && (
                <div>
                  <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Extracted Text Preview
                  </p>
                  <pre className="max-h-40 overflow-y-auto rounded-md border bg-muted/40 p-3 font-mono text-xs whitespace-pre-wrap">
                    {inspectedDoc.extracted_preview}
                  </pre>
                </div>
              )}

              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Indexed Chunks ({inspectedDoc.chunks.length})
                </p>
                <div className="space-y-3">
                  {inspectedDoc.chunks.map((chunk) => (
                    <div key={chunk.id} className="rounded-md border p-3.5">
                      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                        <span className="font-medium text-foreground">
                          Chunk #{chunk.chunk_index}
                          {chunk.section_heading ? ` • ${chunk.section_heading}` : ""}
                        </span>
                        <span>
                          {chunk.page_number ? `Page ${chunk.page_number}` : "No page"} •{" "}
                          {chunk.token_count} tokens • {chunk.embedding_model} ({chunk.embedding_dim}d)
                        </span>
                      </div>
                      <p className="whitespace-pre-wrap font-mono text-xs leading-relaxed">
                        {chunk.cleaned_content}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

