"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { User } from "@/lib/types";
import { api, getStoredToken, setStoredToken } from "@/services/api";

const DEFAULT_WORKSPACE_EMAIL =
  process.env.NEXT_PUBLIC_DEFAULT_USER_EMAIL || "admin@novatech-demo.internal";
const DEFAULT_WORKSPACE_PASSWORD =
  process.env.NEXT_PUBLIC_DEFAULT_USER_PASSWORD || "AdminDemo!2026";
const MANUAL_LOGOUT_KEY = "helpdesk_ai_manual_logout";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: {
    email: string;
    full_name: string;
    department: string;
    password: string;
  }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const token = getStoredToken();
      if (token) {
        try {
          const profile = await api.me();
          setUser(profile);
          setLoading(false);
          return;
        } catch {
          setStoredToken(null);
        }
      }

      // Single-user seamless workspace mode: auto-connect unless explicitly signed out
      const manuallySignedOut =
        typeof window !== "undefined" &&
        window.sessionStorage.getItem(MANUAL_LOGOUT_KEY) === "true";

      if (!manuallySignedOut) {
        try {
          const res = await api.login(DEFAULT_WORKSPACE_EMAIL, DEFAULT_WORKSPACE_PASSWORD);
          setStoredToken(res.access_token);
          setUser(res.user);
        } catch {
          setUser(null);
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    if (typeof window !== "undefined") {
      window.sessionStorage.removeItem(MANUAL_LOGOUT_KEY);
    }
    const res = await api.login(email, password);
    setStoredToken(res.access_token);
    setUser(res.user);
  }, []);

  const register = useCallback(
    async (payload: {
      email: string;
      full_name: string;
      department: string;
      password: string;
    }) => {
      if (typeof window !== "undefined") {
        window.sessionStorage.removeItem(MANUAL_LOGOUT_KEY);
      }
      const res = await api.register(payload);
      setStoredToken(res.access_token);
      setUser(res.user);
    },
    []
  );

  const logout = useCallback(() => {
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(MANUAL_LOGOUT_KEY, "true");
    }
    setStoredToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
