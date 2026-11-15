"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { MessageSquare, Trash2 } from "lucide-react";
import type { ConversationSummary } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";
import { api } from "@/services/api";
import { Button, Card } from "@/components/ui/primitives";

export default function HistoryPage() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const list = await api.listConversations();
      setConversations(list);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (id: string) => {
    await api.deleteConversation(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
  };

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Conversation History</h1>
          <p className="text-xs text-muted-foreground">
            Private to your account. Reopen previous troubleshooting threads or remove them.
          </p>
        </div>
        <Link href="/chat">
          <Button size="sm">New Conversation</Button>
        </Link>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading conversations...</p>
      ) : conversations.length === 0 ? (
        <Card className="p-8 text-center text-sm text-muted-foreground">
          You have no saved conversations yet.
        </Card>
      ) : (
        <div className="space-y-3">
          {conversations.map((conv) => (
            <Card key={conv.id} className="flex items-center justify-between gap-4 p-4">
              <Link
                href={`/chat?conversationId=${conv.id}`}
                className="min-w-0 flex-1 space-y-1 hover:opacity-80"
              >
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 shrink-0 text-primary" />
                  <p className="truncate text-sm font-semibold">{conv.title}</p>
                </div>
                {conv.last_message_preview && (
                  <p className="truncate text-xs text-muted-foreground">
                    {conv.last_message_preview}
                  </p>
                )}
                <p className="text-[11px] text-muted-foreground">
                  {conv.message_count} messages • Updated {formatDateTime(conv.updated_at)}
                </p>
              </Link>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleDelete(conv.id)}
                title="Delete conversation"
              >
                <Trash2 className="h-4 w-4 text-rose-500" />
              </Button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

