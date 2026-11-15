"use client";

import React, { useState } from "react";
import { Lock, Moon, ShieldCheck, Sparkles, Sun } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useTheme } from "@/hooks/useTheme";
import { Button, Card, Input } from "@/components/ui/primitives";

const DEMO_ACCOUNTS = [
  {
    label: "Admin",
    email: "admin@novatech-demo.internal",
    password: "AdminDemo!2026",
  },
  {
    label: "IT Staff",
    email: "itstaff@novatech-demo.internal",
    password: "ItStaffDemo!2026",
  },
  {
    label: "Employee",
    email: "employee@novatech-demo.internal",
    password: "EmployeeDemo!2026",
  },
];

export function AuthScreen() {
  const { login, register } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [department, setDepartment] = useState("Product Engineering");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register({
          email,
          full_name: fullName,
          department,
          password,
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md p-6 sm:p-8">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight">KnowBase AI</h1>
              <p className="text-xs text-muted-foreground">
                Your Knowledge. One Intelligent Assistant.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={toggleTheme}
            className="flex h-8 w-8 items-center justify-center rounded-md border text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            title="Toggle theme"
          >
            {theme === "light" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
          </button>
        </div>

        <div className="mb-5 flex rounded-md bg-muted p-1 text-xs font-medium">
          <button
            type="button"
            onClick={() => {
              setMode("login");
              setError(null);
            }}
            className={`flex-1 rounded py-1.5 transition-colors ${
              mode === "login" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground"
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("register");
              setError(null);
            }}
            className={`flex-1 rounded py-1.5 transition-colors ${
              mode === "register" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground"
            }`}
          >
            Create Employee Account
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === "register" && (
            <>
              <div className="space-y-1.5">
                <label className="text-xs font-medium">Full Name</label>
                <Input
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Alex Rivera"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium">Department</label>
                <Input
                  required
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  placeholder="Engineering"
                />
              </div>
            </>
          )}

          <div className="space-y-1.5">
            <label className="text-xs font-medium">Corporate Email</label>
            <Input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@novatech-demo.internal"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium">Password</label>
            <Input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div className="rounded-md border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-600 dark:text-rose-400">
              {error}
            </div>
          )}

          <Button type="submit" className="w-full" disabled={submitting}>
            <Lock className="h-3.5 w-3.5" />
            {submitting
              ? "Authenticating..."
              : mode === "login"
              ? "Sign In"
              : "Register & Sign In"}
          </Button>
        </form>

        {mode === "login" && (
          <div className="mt-6 border-t pt-4">
            <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              Demo Environment Quick Fill
            </p>
            <div className="grid grid-cols-3 gap-2">
              {DEMO_ACCOUNTS.map((acc) => (
                <button
                  key={acc.label}
                  type="button"
                  onClick={() => {
                    setEmail(acc.email);
                    setPassword(acc.password);
                  }}
                  className="rounded-md border bg-muted/50 px-2 py-1.5 text-xs font-medium hover:bg-muted"
                >
                  {acc.label}
                </button>
              ))}
            </div>
            <p className="mt-2.5 text-[11px] text-muted-foreground">
              Synthetic demonstration workspace using fictional NovaTech Global documentation.
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}

