"use client";

import React, { useEffect, useState } from "react";
import { CheckCircle2, ShieldAlert, XCircle } from "lucide-react";
import type { SystemConfig } from "@/lib/types";
import { api } from "@/services/api";
import { Badge, Card } from "@/components/ui/primitives";

export default function AdminConfigPage() {
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getSystemConfig()
      .then(setConfig)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load configuration."));
  }, []);

  if (error) return <Card className="p-6 text-sm text-rose-500">{error}</Card>;
  if (!config) return <div className="text-sm text-muted-foreground">Loading configuration...</div>;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">System Configuration</h1>
        <p className="text-xs text-muted-foreground">
          Live execution mode, model pipeline parameters, and vector database health (secrets are never exposed).
        </p>
      </div>

      <Card className="border-amber-500/30 bg-amber-500/10 p-4 text-xs text-amber-800 dark:text-amber-300">
        <div className="flex items-start gap-2.5">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{config.security_notice}</p>
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="space-y-3 p-5 text-xs">
          <h2 className="text-sm font-semibold">AI Execution Mode & Provider</h2>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Execution Mode</span>
            <Badge variant="default">
              {config.ai_execution_mode === "local" ? "Mode A: Local AI" : "Mode B: Cloud AI"}
            </Badge>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Active Provider / Model</span>
            <span className="font-mono font-medium">
              {config.active_provider} / {config.active_model}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Ollama Service ({config.ollama_base_url})</span>
            <span className="inline-flex items-center gap-1 font-medium">
              {config.ollama_available ? (
                <>
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> Available
                </>
              ) : (
                <>
                  <XCircle className="h-3.5 w-3.5 text-amber-500" /> Offline
                </>
              )}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Cloud Gemini API Key</span>
            <span>{config.gemini_configured ? "Configured (Backend Only)" : "Not Set"}</span>
          </div>
        </Card>

        <Card className="space-y-3 p-5 text-xs">
          <h2 className="text-sm font-semibold">Vector DB & Retrieval Pipeline</h2>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Database / Dialect</span>
            <span className="font-mono">
              {config.database_status.connected ? "Connected" : "Disconnected"} (
              {config.database_status.dialect})
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">pgvector Extension</span>
            <span>{config.database_status.pgvector_enabled ? "Enabled" : "Inactive / Test Mode"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Embedding Model</span>
            <span className="font-mono">
              {config.embedding_model} ({config.embedding_dim}d)
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Cross-Encoder Reranker</span>
            <span className="font-mono">
              {config.enable_reranking ? config.reranker_model : "Disabled"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Chunking / RRF Weights</span>
            <span className="font-mono">
              {config.chunk_size}/{config.chunk_overlap} • sem {config.semantic_weight} / bm25{" "}
              {config.bm25_weight}
            </span>
          </div>
        </Card>
      </div>
    </div>
  );
}

