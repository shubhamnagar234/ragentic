import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Sparkles } from "lucide-react";
import { HeroAnimation } from "@/components/landing/HeroAnimation";
import { FeaturesGrid } from "@/components/landing/FeaturesGrid";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

export default async function LandingPage() {
  const session = await auth();

  if (session) {
    redirect("/workspaces");
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Navbar */}
      <nav className="h-12 border-b border-border flex items-center px-6 gap-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="font-heading font-semibold text-sm">RAGENTIC</span>
        </div>
        <div className="flex-1" />
        <ThemeToggle />
        <Link href="/signin">
          <Button size="sm">Sign in</Button>
        </Link>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 py-24 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-border bg-muted text-xs font-medium text-muted-foreground mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
          Self-healing agentic RAG platform
        </div>

        <h1 className="font-heading text-5xl font-bold tracking-tight mb-6 leading-tight">
          Your knowledge,{" "}
          <span className="text-primary">intelligently retrieved</span>
        </h1>

        <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
          Paste any link — YouTube, GitHub, PDF, web page — and ask questions
          across all your sources simultaneously. Powered by hybrid RAG,
          LangGraph agents, and real-time self-healing.
        </p>

        <div className="flex items-center justify-center gap-3 mb-12">
          <Link href="/signin">
            <Button
              size="lg"
              className="gap-2 rounded-full shadow-sm hover:shadow-md transition-shadow"
            >
              <Sparkles className="w-4 h-4" />
              Get started
            </Button>
          </Link>
        </div>
      </section>

      {/* Hero Animation */}
      <section className="max-w-6xl mx-auto px-6 pb-24">
        <HeroAnimation />
      </section>

      {/* Features */}
      <section className="max-w-5xl mx-auto px-6 py-16">
        <FeaturesGrid />
      </section>

      {/* CTA */}
      <section className="max-w-2xl mx-auto px-6 py-16 text-center">
        <h2 className="font-heading text-2xl font-bold mb-3">
          Ready to build your knowledge workspace?
        </h2>
        <p className="text-muted-foreground mb-6">
          Free to use. No credit card required.
        </p>
        <Link href="/signin">
          <Button size="lg" className="gap-2">
            <Sparkles className="w-4 h-4" />
            Get started
          </Button>
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-6 text-center text-xs text-muted-foreground">
        RAGENTIC — Multimodal AI Knowledge Workspace
      </footer>
    </div>
  );
}
