import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Sparkles,
  Brain,
  Shield,
  RefreshCw,
  BarChart2,
  GitBranch,
} from "lucide-react";

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

        <div className="flex items-center justify-center gap-3">
          <Link href="/signin">
            <Button size="lg" className="gap-2">
              <Sparkles className="w-4 h-4" />
              Get started
            </Button>
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-5xl mx-auto px-6 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            {
              icon: Brain,
              title: "Hybrid retrieval",
              description:
                "BM25 + vector search + cross-encoder reranker. Measurably better than pure vector search.",
              color: "bg-blue-500/10 text-blue-600",
            },
            {
              icon: RefreshCw,
              title: "Self-healing",
              description:
                "Critic agent scores every retrieval. Low confidence triggers automatic query rewriting and re-retrieval.",
              color: "bg-amber-500/10 text-amber-600",
            },
            {
              icon: Shield,
              title: "RAGAS evaluation",
              description:
                "Every response scored for faithfulness, context precision, and answer relevance. Real metrics, not marketing.",
              color: "bg-green-500/10 text-green-600",
            },
            {
              icon: BarChart2,
              title: "Real-time observability",
              description:
                "Watch every agent node fire in real time. Timeline shows exactly how your answer was built.",
              color: "bg-purple-500/10 text-purple-600",
            },
            {
              icon: GitBranch,
              title: "Any source",
              description:
                "YouTube, GitHub repos, PDFs, web pages, audio files. One input box handles everything.",
              color: "bg-gray-500/10 text-gray-600",
            },
            {
              icon: Sparkles,
              title: "Confidence scoring",
              description:
                "Knows when it doesn't know. Low-confidence answers are flagged explicitly — no hallucinating confidently.",
              color: "bg-red-500/10 text-red-600",
            },
          ].map((feature) => (
            <div
              key={feature.title}
              className="border border-border rounded-xl p-5 bg-card hover:border-primary/30 transition-colors"
            >
              <div
                className={`w-9 h-9 rounded-lg flex items-center justify-center mb-3 ${feature.color}`}
              >
                <feature.icon className="w-4 h-4" />
              </div>
              <h3 className="font-heading font-semibold text-sm mb-1.5">
                {feature.title}
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
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
