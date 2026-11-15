"use client";

import React from "react";
import { FileText, X } from "lucide-react";
import type { Citation } from "@/lib/types";
import { Badge, Button } from "@/components/ui/primitives";

export function CitationDrawer({
  citation,
  onClose,
}: {
  citation: Citation | null;
  onClose: () => void;
}) {
  if (!citation) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="fixed inset-0 bg-black/40" onClick={onClose} />
      <div className="relative z-10 flex h-full w-full max-w-lg flex-col border-l bg-card shadow-xl">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold">Source Passage Inspector</h3>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-5">
          <div>
            <p className="text-xs text-muted-foreground">Document Title</p>
            <p className="mt-0.5 text-base font-semibold">{citation.document_title}</p>
          </div>

          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">File: {citation.original_filename}</Badge>
            <Badge variant="outline">
              {citation.page_number !== null && citation.page_number !== undefined
                ? `Page ${citation.page_number}`
                : "Page reference unavailable"}
            </Badge>
            {citation.chunk_index !== null && citation.chunk_index !== undefined && (
              <Badge variant="outline">Chunk #{citation.chunk_index}</Badge>
            )}
            <Badge variant="default">
              Relevance: {(citation.relevance_score * 100).toFixed(0)}%
            </Badge>
          </div>

          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Retrieved Evidence Excerpt
            </p>
            <div className="rounded-md border bg-muted/40 p-4 font-mono text-xs leading-relaxed whitespace-pre-wrap">
              {citation.passage_excerpt}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

