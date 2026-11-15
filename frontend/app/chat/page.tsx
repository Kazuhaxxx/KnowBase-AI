"use client";

import React, { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ChatInterface } from "@/components/chat/ChatInterface";

function ChatPageInner() {
  const params = useSearchParams();
  const conversationId = params.get("conversationId");
  const prompt = params.get("prompt");
  return <ChatInterface initialConversationId={conversationId} initialPrompt={prompt} />;
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="text-sm text-muted-foreground">Loading chat...</div>}>
      <ChatPageInner />
    </Suspense>
  );
}

