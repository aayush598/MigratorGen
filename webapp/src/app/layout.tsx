import type { Metadata } from "next";
import { ClerkAuthProvider } from "@/lib/clerk-utils";
import "./globals.css";

export const metadata: Metadata = {
  title: "MigratorGen — Python Library Migration Platform",
  description: "Automate Python library migrations with AST-accurate, transaction-safe transformations.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="antialiased">
      <body className="min-h-screen bg-[#fafafa]">
        <ClerkAuthProvider>{children}</ClerkAuthProvider>
      </body>
    </html>
  );
}
