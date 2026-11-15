"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, CheckCircle2, FileText, MessageSquare, ThumbsUp } from "lucide-react";
import type { AdminOverview } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";
import { api } from "@/services/api";
import { Badge, Button, Card } from "@/components/ui/primitives";

export default function AdminOverviewPage() {
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getAdminOverview()
      .then(setOverview)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load admin overview."));
  }, []);

  if (error) {
    return <Card className="p-6 text-sm text-rose-600 dark:text-rose-400">{error}</Card>;
  }
  if (!overview) {
    return <div className="text-sm text-muted-foreground">Loading admin overview...</div>;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Administrator Overview</h1>
          <p className="text-xs text-muted-foreground">
            Knowledge base health, employee support volume, and retrieval telemetry summary.
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/admin/documents">
            <Button size="sm">Manage Documents</Button>
          </Link>
          <Link href="/admin/evaluation">
            <Button size="sm" variant="outline">
              Run RAG Evaluation
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="p-4">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Total Documents</span>
            <FileText className="h-4 w-4 text-primary" />
          </div>
          <p className="mt-2 text-2xl font-semibold">{overview.total_documents}</p>
          <p className="mt-1 text-xs text-muted-foreground">{overview.total_chunks} indexed chunks</p>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Indexed / Failed</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </div>
          <p className="mt-2 text-2xl font-semibold">
            {overview.indexed_documents}{" "}
            <span className="text-sm font-normal text-rose-500">
              / {overview.failed_documents} failed
            </span>
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {overview.pending_documents} pending jobs
          </p>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Support Conversations</span>
            <MessageSquare className="h-4 w-4 text-primary" />
          </div>
          <p className="mt-2 text-2xl font-semibold">{overview.total_conversations}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {overview.total_questions} employee questions
          </p>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>User Feedback</span>
            <ThumbsUp className="h-4 w-4 text-emerald-500" />
          </div>
          <p className="mt-2 text-2xl font-semibold">
            {overview.helpful_feedback} helpful
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {overview.not_helpful_feedback} not helpful
          </p>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <h2 className="mb-4 text-sm font-semibold">Most Requested Categories</h2>
          {overview.top_categories.length === 0 ? (
            <div className="flex items-center gap-2 py-6 text-xs text-muted-foreground">
              <AlertCircle className="h-4 w-4" />
              No chat queries recorded yet. Ask questions in AI Support Chat to populate telemetry.
            </div>
          ) : (
            <div className="space-y-3">
              {overview.top_categories.map((cat) => (
                <div key={cat.category} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium">{cat.category}</span>
                    <span className="text-muted-foreground">{cat.count} queries</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted">
                    <div
                      className="h-2 rounded-full bg-primary"
                      style={{
                        width: `${Math.min(
                          100,
                          (cat.count / Math.max(1, overview.top_categories[0].count)) * 100
                        )}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="p-5">
          <h2 className="mb-4 text-sm font-semibold">Recent Knowledge Base Activity</h2>
          <div className="space-y-2.5">
            {overview.recent_documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between rounded-md border px-3 py-2 text-xs"
              >
                <div className="min-w-0 pr-3">
                  <p className="truncate font-medium">{doc.title}</p>
                  <p className="text-muted-foreground">
                    {doc.category} • {doc.chunk_count} chunks • {formatDateTime(doc.created_at)}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-1.5">
                  <Badge variant="outline">{doc.classification}</Badge>
                  <Badge variant={doc.status === "indexed" ? "success" : "danger"}>
                    {doc.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

