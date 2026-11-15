"use client";

import React, { useEffect, useState } from "react";
import type { AdminAnalytics } from "@/lib/types";
import { Card } from "@/components/ui/primitives";

import { api } from "@/services/api";

export default function AdminAnalyticsPage() {
  const [data, setData] = useState<AdminAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getAdminAnalytics()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load analytics."));
  }, []);

  if (error) return <Card className="p-6 text-sm text-rose-500">{error}</Card>;
  if (!data) return <div className="text-sm text-muted-foreground">Loading analytics...</div>;

  const maxLatency = Math.max(100, ...data.latency_trend.map((t) => t.total_ms));

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Analytics & Telemetry</h1>
        <p className="text-xs text-muted-foreground">
          Non-sensitive operational metrics. Confidential prompts and document contents are never logged.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="p-4">
          <p className="text-xs text-muted-foreground">Total Questions</p>
          <p className="mt-1 text-2xl font-semibold">{data.total_questions}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Across {data.total_conversations} conversations
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-muted-foreground">Avg Total / Retrieval Latency</p>
          <p className="mt-1 text-2xl font-semibold">{data.avg_total_latency_ms} ms</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Retrieval: {data.avg_retrieval_latency_ms} ms • LLM: {data.avg_generation_latency_ms} ms
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-muted-foreground">Evidence Sufficiency Rate</p>
          <p className="mt-1 text-2xl font-semibold">
            {(data.evidence_sufficiency_rate * 100).toFixed(1)}%
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {data.failed_retrieval_count} insufficient-evidence abstentions
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-muted-foreground">Feedback Balance</p>
          <p className="mt-1 text-2xl font-semibold">
            {data.helpful_feedback} / {data.helpful_feedback + data.not_helpful_feedback}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">Helpful ratings</p>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <h2 className="mb-4 text-sm font-semibold">Recent Query Latency Breakdown (ms)</h2>
          {data.latency_trend.length === 0 ? (
            <p className="py-8 text-center text-xs text-muted-foreground">
              No query telemetry recorded yet.
            </p>
          ) : (
            <div className="flex h-44 items-end gap-2 border-b pb-2">
              {data.latency_trend.map((pt) => (
                <div key={pt.index} className="flex flex-1 flex-col items-center gap-1">
                  <div
                    className={`w-full rounded-t ${
                      pt.sufficient ? "bg-primary/80" : "bg-amber-500/80"
                    }`}
                    style={{ height: `${Math.max(8, (pt.total_ms / maxLatency) * 140)}px` }}
                    title={`#${pt.index}: Total ${pt.total_ms}ms (Retrieval ${pt.retrieval_ms}ms)`}
                  />
                  <span className="text-[10px] text-muted-foreground">{pt.index}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="p-5">
          <h2 className="mb-4 text-sm font-semibold">Frequently Cited Documents</h2>
          {data.frequently_retrieved_documents.length === 0 ? (
            <p className="py-8 text-center text-xs text-muted-foreground">
              No cited documents recorded yet.
            </p>
          ) : (
            <div className="space-y-2.5">
              {data.frequently_retrieved_documents.map((d) => (
                <div
                  key={d.document_id}
                  className="flex items-center justify-between rounded border px-3 py-2 text-xs"
                >
                  <span className="truncate font-medium">{d.title}</span>
                  <span className="shrink-0 pl-2 text-muted-foreground">{d.count} citations</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

