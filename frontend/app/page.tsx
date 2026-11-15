"use client";

import React, { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ChatInterface } from "@/components/chat/ChatInterface";

function HomeChatInner() {
  const params = useSearchParams();
  const conversationId = params.get("conversationId");
  const prompt = params.get("prompt");
  return <ChatInterface initialConversationId={conversationId} initialPrompt={prompt} />;
}

export default function HomePage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
          Loading HelpDesk AI...
        </div>
      }
    >
      <HomeChatInner />
    </Suspense>
  );
}
