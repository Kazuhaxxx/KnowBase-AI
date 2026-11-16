import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/hooks/useAuth";
import { ThemeProvider } from "@/hooks/useTheme";
import { AuthGate } from "@/components/layout/AuthGate";

export const metadata: Metadata = {
  title: "KnowBase AI — Your Knowledge. One Intelligent Assistant.",
  description:
    "Enterprise AI knowledge management platform powered by Hybrid RAG, Cross-Encoder Reranking, Collections, and RBAC.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>
        <ThemeProvider>
          <AuthProvider>
            <AuthGate>{children}</AuthGate>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

