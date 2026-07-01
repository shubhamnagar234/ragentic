import type { Metadata } from "next";
import { Inter, Manrope } from "next/font/google";
import "./globals.css";
import Providers from "@/components/layout/Providers";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RAGENTIC — Multimodal AI Knowledge Workspace",
  description:
    "Self-healing agentic RAG platform with hybrid retrieval, LangGraph orchestration, and real-time observability",
  openGraph: {
    title: "RAGENTIC",
    description: "Multimodal AI Knowledge Workspace",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${manrope.variable} antialiased`}>
          <Providers>{children}</Providers>
      </body>
    </html>
  );
}
