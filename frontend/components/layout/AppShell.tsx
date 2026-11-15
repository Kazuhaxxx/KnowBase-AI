"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  BookOpen,
  FlaskConical,
  FolderTree,
  Menu,
  MessageSquare,
  Moon,
  Plus,
  Search,
  Sparkles,
  Sun,
  Trash2,
  X,
} from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import type { ConversationSummary } from "@/lib/types";
import { cn } from "@/lib/utils";
import { api } from "@/services/api";
import { Button } from "@/components/ui/primitives";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeConversationId = searchParams.get("conversationId");
  const { theme, toggleTheme } = useTheme();

  const [mobileOpen, setMobileOpen] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [searchQuery, setSearchQuery] = useState("");

  const refreshConversations = useCallback(async (query?: string) => {
    try {
      const list = await api.listConversations(query);
      setConversations(list);
    } catch {
      // ignore background list refresh errors
    }
  }, []);

  useEffect(() => {
    refreshConversations(searchQuery);
    const handler = () => refreshConversations(searchQuery);
    window.addEventListener("helpdesk:conversations-updated", handler);
    return () => window.removeEventListener("helpdesk:conversations-updated", handler);
  }, [refreshConversations, searchQuery]);

  const handleNewChat = () => {
    setMobileOpen(false);
    window.dispatchEvent(new CustomEvent("helpdesk:new-chat"));
    router.push("/");
  };

  const handleDeleteConversation = async (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    await api.deleteConversation(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeConversationId === id) {
      router.push("/");
    }
  };

  const sidebarContent = (
    <div className="flex h-full flex-col justify-between p-3">
      {/* Top: Brand + New Chat */}
      <div className="space-y-3">
        <div className="flex items-center justify-between px-1.5 pt-1">
          <Link href="/" className="flex items-center gap-2" onClick={() => setMobileOpen(false)}>
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <span className="text-sm font-semibold tracking-tight">KnowBase AI</span>
            </div>
          </Link>
          <button
            type="button"
            className="rounded-md p-1 text-muted-foreground hover:bg-muted lg:hidden"
            onClick={() => setMobileOpen(false)}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <Button
          variant="outline"
          className="w-full justify-start gap-2 bg-background font-medium"
          onClick={handleNewChat}
        >
          <Plus className="h-4 w-4" />
          New Chat
        </Button>

        {/* Conversation Search Bar */}
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversations..."
            className="w-full rounded-md border border-input bg-background/50 py-1.5 pl-8 pr-2.5 text-xs placeholder:text-muted-foreground focus:border-primary focus:outline-none"
          />
        </div>
      </div>

      {/* Middle: ChatGPT-style Conversation List */}
      <div className="my-3 flex-1 overflow-y-auto pr-1">
        <p className="px-2 pb-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          Chats
        </p>
        {conversations.length === 0 ? (
          <p className="px-2 py-3 text-xs text-muted-foreground">
            Your conversations will appear here.
          </p>
        ) : (
          <div className="space-y-0.5">
            {conversations.map((conv) => {
              const isActive =
                (pathname === "/" || pathname === "/chat") && activeConversationId === conv.id;
              return (
                <Link
                  key={conv.id}
                  href={`/?conversationId=${conv.id}`}
                  onClick={() => setMobileOpen(false)}
                  className={cn(
                    "group flex items-center justify-between gap-2 rounded-md px-2.5 py-2 text-xs transition-colors",
                    isActive
                      ? "bg-primary/10 font-medium text-primary"
                      : "text-foreground/80 hover:bg-muted"
                  )}
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <MessageSquare className="h-3.5 w-3.5 shrink-0 opacity-60" />
                    <span className="truncate">{conv.title}</span>
                  </span>
                  <button
                    type="button"
                    onClick={(e) => handleDeleteConversation(e, conv.id)}
                    className="hidden shrink-0 rounded p-0.5 text-muted-foreground hover:text-rose-500 group-hover:inline-flex"
                    title="Delete chat"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </Link>
              );
            })}
          </div>
        )}
      </div>

      {/* Bottom: Knowledge Docs + Eval + Theme */}
      <div className="space-y-1 border-t pt-3">
        <Link
          href="/knowledge"
          onClick={() => setMobileOpen(false)}
          className={cn(
            "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-xs font-medium transition-colors",
            pathname === "/knowledge"
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <BookOpen className="h-4 w-4" />
          Knowledge & Upload
        </Link>

        <Link
          href="/admin/evaluation"
          onClick={() => setMobileOpen(false)}
          className={cn(
            "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-xs font-medium transition-colors",
            pathname === "/admin/evaluation"
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <FlaskConical className="h-4 w-4" />
          RAG Benchmark
        </Link>

        <button
          type="button"
          onClick={toggleTheme}
          className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          {theme === "light" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
          {theme === "light" ? "Dark Mode" : "Light Mode"}
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Desktop Sidebar */}
      <aside className="hidden w-64 shrink-0 border-r bg-card lg:block">{sidebarContent}</aside>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div className="fixed inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
          <aside className="relative z-10 w-64 border-r bg-card">{sidebarContent}</aside>
        </div>
      )}

      {/* Main Content */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-12 shrink-0 items-center justify-between border-b bg-card px-4 lg:hidden">
          <button
            type="button"
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </button>
          <span className="text-sm font-semibold">KnowBase AI</span>
          <button
            type="button"
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted"
            onClick={handleNewChat}
            title="New chat"
          >
            <Plus className="h-5 w-5" />
          </button>
        </header>

        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
