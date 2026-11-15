"use client";

import React, { useEffect, useState } from "react";
import { FlaskConical, Play } from "lucide-react";
import type { EvaluationRun } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";
import { api } from "@/services/api";
import { Badge, Button, Card } from "@/components/ui/primitives";

export default function AdminEvaluationPage() {
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setRuns(await api.listEvaluations());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load evaluation history.");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleRunComparison = async () => {
    setRunning(true);
    setError(null);
    try {
      const fresh = await api.runEvaluation(["semantic", "hybrid", "hybrid_rerank"], 5);
      setRuns((prev) => [...fresh, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evaluation failed.");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">RAG Retrieval Evaluation</h1>
          <p className="text-xs text-muted-foreground">
            Quantitative comparison of Semantic Only vs Hybrid (BM25 + RRF) vs Hybrid + Cross-Encoder Reranking on the 60-question benchmark.
          </p>
        </div>
        <Button onClick={handleRunComparison} disabled={running}>
          <Play className="h-4 w-4" />
          {running ? "Running Benchmark (60 Qs × 3 Modes)..." : "Run 3-Mode Benchmark"}
        </Button>
      </div>

      {error && (
        <Card className="border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-500">
          {error}
        </Card>
      )}

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b bg-muted/40 text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-semibold">Run</th>
                <th className="px-4 py-3 font-semibold">Mode</th>
                <th className="px-4 py-3 font-semibold">Recall@K</th>
                <th className="px-4 py-3 font-semibold">Precision@K</th>
                <th className="px-4 py-3 font-semibold">MRR</th>
                <th className="px-4 py-3 font-semibold">Context Relevance</th>
                <th className="px-4 py-3 font-semibold">Type</th>
                <th className="px-4 py-3 font-semibold">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {runs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-muted-foreground">
                    <div className="flex flex-col items-center gap-2">
                      <FlaskConical className="h-5 w-5" />
                      <span>No evaluation runs recorded yet. Click &quot;Run 3-Mode Benchmark&quot; to execute.</span>
                    </div>
                  </td>
                </tr>
              ) : (
                runs.map((r) => (
                  <tr key={r.id} className="hover:bg-muted/20">
                    <td className="px-4 py-3 font-medium">
                      {r.run_name} ({r.question_count} Qs, K={r.k_value})
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="default">{r.retrieval_mode}</Badge>
                    </td>
                    <td className="px-4 py-3 font-mono font-semibold">
                      {(r.recall_at_k * 100).toFixed(1)}%
                    </td>
                    <td className="px-4 py-3 font-mono">
                      {(r.precision_at_k * 100).toFixed(1)}%
                    </td>
                    <td className="px-4 py-3 font-mono font-semibold">{r.mrr.toFixed(4)}</td>
                    <td className="px-4 py-3 font-mono">
                      {(r.context_relevance * 100).toFixed(1)}%
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="outline">
                        {r.llm_evaluated ? "Automated + LLM Judge" : "Automated Deterministic"}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {formatDateTime(r.created_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

