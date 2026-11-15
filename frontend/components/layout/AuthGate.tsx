"use client";

import React, { Suspense } from "react";
import { useAuth } from "@/hooks/useAuth";
import { AuthScreen } from "@/components/auth/AuthScreen";
import { AppShell } from "@/components/layout/AppShell";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background text-sm text-muted-foreground">
        Loading HelpDesk AI...
      </div>
    );
  }

  if (!user) {
    return <AuthScreen />;
  }

  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-background text-sm text-muted-foreground">
          Loading workspace...
        </div>
      }
    >
      <AppShell>{children}</AppShell>
    </Suspense>
  );
}
