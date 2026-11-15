"use client";

import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  AlertTriangle,
  ArrowUp,
  Bot,
  Check,
  Copy,
  FileText,
  FolderTree,
  RotateCcw,
  ShieldAlert,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  User as UserIcon,
} from "lucide-react";
import type { ChatMessage, Citation, Collection } from "@/lib/types";
import { api, streamChat } from "@/services/api";
import { CitationDrawer } from "@/components/chat/CitationDrawer";

const SUGGESTED_QUESTIONS = [
  "How do I troubleshoot Outlook authentication issues?",
  "What is the procedure for requesting system access?",
  "Summarise the company's remote working policy.",
  "What are the steps for reporting a technical incident?",
  "Find the documentation related to VPN configuration.",
];

export function ChatInterface({
  initialConversationId,
  initialPrompt,
}: {
  initialConversationId?: string | null;
  initialPrompt?: string | null;
}) {
  const [conversationId, setConversationId] = useState<string | null>(
    initialConversationId || null
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState(initialPrompt || "");
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState<string | null>(null);
  const [retrievalMode, setRetrievalMode] = useState<"hybrid_rerank" | "hybrid" | "semantic">(
    "hybrid_rerank"
  );
  const [streamingText, setStreamingText] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [feedbackMap, setFeedbackMap] = useState<Record<string, "helpful" | "not_helpful">>({});
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.listCollections().then(setCollections).catch(() => {});
  }, []);

  useEffect(() => {
    const onNewChat = () => {
      setConversationId(null);
      setMessages([]);
      setError(null);
      setStreamingText("");
    };
    window.addEventListener("helpdesk:new-chat", onNewChat);
    return () => window.removeEventListener("helpdesk:new-chat", onNewChat);
  }, []);

  useEffect(() => {
    if (!initialConversationId) {
      setConversationId(null);
      setMessages([]);
      return;
    }
    api
      .getConversation(initialConversationId)
      .then((conv) => {
        setConversationId(conv.id);
        setMessages(conv.messages);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load conversation."));
  }, [initialConversationId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  const handleSend = async (promptOverride?: string) => {
    const question = (promptOverride ?? input).trim();
    if (!question || isSending) return;

    setError(null);
    if (!promptOverride) setInput("");
    setIsSending(true);
    setStreamingText("");

    const optimisticUser: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: question,
      citations: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticUser]);

    await streamChat(
      {
        question,
        conversation_id: conversationId,
        collection_id: selectedCollectionId,
        retrieval_mode: retrievalMode,
      },
      {
        onToken: (token) => {
          setStreamingText((prev) => prev + token);
        },
        onDone: (res) => {
          setConversationId(res.conversation_id);
          setMessages((prev) => [
            ...prev.filter((m) => m.id !== optimisticUser.id),
            res.user_message,
            res.assistant_message,
          ]);
          setStreamingText("");
          setIsSending(false);
          window.dispatchEvent(new CustomEvent("helpdesk:conversations-updated"));
        },
        onError: (detail) => {
          setError(detail);
          setStreamingText("");
          setIsSending(false);
        },
      }
    );
  };

  const handleRegenerate = async (assistantMessageId: string) => {
    if (isSending) return;
    const msgIndex = messages.findIndex((m) => m.id === assistantMessageId);
    if (msgIndex === -1) return;

    // Find the immediately preceding user turn
    let lastUserPrompt = "";
    for (let i = msgIndex - 1; i >= 0; i--) {
      if (messages[i].role === "user") {
        lastUserPrompt = messages[i].content;
        break;
      }
    }
    if (lastUserPrompt) {
      await handleSend(lastUserPrompt);
    }
  };

  const handleCopy = async (id: string, text: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleFeedback = async (messageId: string, rating: "helpful" | "not_helpful") => {
    try {
      await api.sendFeedback(messageId, rating);
      setFeedbackMap((prev) => ({ ...prev, [messageId]: rating }));
    } catch {
      // ignore transient feedback error
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Top Bar with Knowledge Scope & Retrieval Mode */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b bg-card/60 px-4 py-2.5 backdrop-blur sm:px-6">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Sparkles className="h-3.5 w-3.5" />
          </div>
          <span className="text-sm font-semibold tracking-tight">KnowBase AI</span>
          <span className="hidden text-xs text-muted-foreground md:inline">
            • Your Knowledge. One Intelligent Assistant.
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Collection Filter */}
          <div className="flex items-center gap-1.5">
            <FolderTree className="h-3.5 w-3.5 text-muted-foreground" />
            <select
              value={selectedCollectionId || ""}
              onChange={(e) => setSelectedCollectionId(e.target.value || null)}
              className="h-8 rounded-md border border-input bg-background px-2 text-xs font-medium focus:border-primary focus:outline-none"
              aria-label="Filter collection"
            >
              <option value="">All Collections</option>
              {collections.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.document_count})
                </option>
              ))}
            </select>
          </div>

          {/* Retrieval Engine Mode */}
          <select
            value={retrievalMode}
            onChange={(e) =>
              setRetrievalMode(e.target.value as "hybrid_rerank" | "hybrid" | "semantic")
            }
            className="h-8 rounded-md border border-input bg-background px-2 text-xs font-medium focus:border-primary focus:outline-none"
            aria-label="Retrieval mode"
          >
            <option value="hybrid_rerank">Hybrid + CrossEncoder Rerank</option>
            <option value="hybrid">Hybrid (BM25 + Semantic)</option>
            <option value="semantic">Semantic Vector Only</option>
          </select>
        </div>
      </div>

      {/* Centered ChatGPT-Style Message Stream */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-3xl space-y-6">
          {messages.length === 0 && !streamingText && (
            <div className="flex flex-col items-center justify-center py-10 text-center sm:py-16">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary shadow-inner">
                <Bot className="h-7 w-7" />
              </div>
              <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
                What would you like to know?
              </h1>
              <p className="mt-2 max-w-md text-xs leading-relaxed text-muted-foreground sm:text-sm">
                Ask questions about your organisation&apos;s knowledge base. Get answers backed by your documents.
              </p>

              <div className="mt-8 grid w-full gap-2.5 sm:grid-cols-2">
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => handleSend(q)}
                    className="rounded-xl border border-input/60 bg-card p-3.5 text-left text-xs leading-relaxed shadow-sm transition-all hover:border-primary/40 hover:bg-muted/80"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "assistant" && (
                <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <Bot className="h-4 w-4" />
                </div>
              )}

              <div
                className={
                  msg.role === "user"
                    ? "max-w-[80%] rounded-2xl bg-primary px-4 py-2.5 text-sm text-primary-foreground"
                    : "min-w-0 flex-1 space-y-2.5 text-sm text-foreground"
                }
              >
                {msg.role === "assistant" ? (
                  <>
                    {msg.evidence_sufficient === false && (
                      <div className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
                        <ShieldAlert className="h-4 w-4 shrink-0" />
                        Insufficient knowledge base coverage — abstained instead of guessing.
                      </div>
                    )}

                    <div className="prose-chat text-sm leading-relaxed">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    </div>

                    {msg.citations && msg.citations.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {msg.citations.map((cit, idx) => (
                          <button
                            key={cit.id}
                            type="button"
                            onClick={() => setSelectedCitation(cit)}
                            className="inline-flex items-center gap-1.5 rounded-full border bg-card px-2.5 py-1 text-xs font-medium shadow-sm transition-colors hover:border-primary hover:text-primary"
                          >
                            <FileText className="h-3 w-3" />
                            <span>
                              [{idx + 1}] {cit.document_title}
                            </span>
                            {cit.page_number ? (
                              <span className="text-[10px] text-muted-foreground">
                                p.{cit.page_number}
                              </span>
                            ) : null}
                          </button>
                        ))}
                      </div>
                    )}

                    <div className="flex items-center gap-2 pt-1 text-[11px] text-muted-foreground">
                      <button
                        type="button"
                        onClick={() => handleCopy(msg.id, msg.content)}
                        className="rounded p-1 transition-colors hover:bg-muted"
                        title="Copy answer"
                      >
                        {copiedId === msg.id ? (
                          <Check className="h-3.5 w-3.5 text-emerald-500" />
                        ) : (
                          <Copy className="h-3.5 w-3.5" />
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRegenerate(msg.id)}
                        className="rounded p-1 transition-colors hover:bg-muted"
                        title="Regenerate response"
                      >
                        <RotateCcw className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleFeedback(msg.id, "helpful")}
                        className={`rounded p-1 transition-colors hover:bg-muted ${
                          feedbackMap[msg.id] === "helpful" ? "text-emerald-500" : ""
                        }`}
                        title="Helpful"
                      >
                        <ThumbsUp className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleFeedback(msg.id, "not_helpful")}
                        className={`rounded p-1 transition-colors hover:bg-muted ${
                          feedbackMap[msg.id] === "not_helpful" ? "text-rose-500" : ""
                        }`}
                        title="Not helpful"
                      >
                        <ThumbsDown className="h-3.5 w-3.5" />
                      </button>
                      {msg.total_latency_ms ? (
                        <span className="ml-1 text-[10px]">
                          {Math.round(msg.total_latency_ms)} ms • {msg.model_used}
                        </span>
                      ) : null}
                    </div>
                  </>
                ) : (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                )}
              </div>

              {msg.role === "user" && (
                <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
                  <UserIcon className="h-3.5 w-3.5" />
                </div>
              )}
            </div>
          ))}

          {isSending && (
            <div className="flex gap-3">
              <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                <Bot className="h-4 w-4 animate-pulse" />
              </div>
              <div className="min-w-0 flex-1 text-sm">
                {streamingText ? (
                  <div className="prose-chat text-sm">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingText}</ReactMarkdown>
                  </div>
                ) : (
                  <span className="text-xs text-muted-foreground">
                    Searching knowledge base & synthesizing verified answer...
                  </span>
                )}
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-xs text-rose-600 dark:text-rose-400">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <p className="font-semibold">Unable to complete response</p>
                <p className="mt-0.5">{error}</p>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Pinned Bottom ChatGPT-Style Composer */}
      <div className="border-t bg-background/95 p-3 backdrop-blur sm:p-4">
        <div className="mx-auto max-w-3xl">
          <div className="flex items-end gap-2 rounded-2xl border bg-card p-2 shadow-sm focus-within:ring-2 focus-within:ring-ring">
            <textarea
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Ask anything about company knowledge, policies, procedures, or IT..."
              className="max-h-40 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm focus:outline-none"
              disabled={isSending}
            />
            <button
              type="button"
              onClick={() => handleSend()}
              disabled={isSending || !input.trim()}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-40"
              aria-label="Send message"
            >
              <ArrowUp className="h-4 w-4" />
            </button>
          </div>
          <p className="mt-1.5 text-center text-[11px] text-muted-foreground">
            Answers are grounded exclusively in verified organizational documents. Click citations to view original sources.
          </p>
        </div>
      </div>

      <CitationDrawer citation={selectedCitation} onClose={() => setSelectedCitation(null)} />
    </div>
  );
}
