import {
  Brain,
  RefreshCw,
  Shield,
  BarChart2,
  GitBranch,
  Sparkles,
} from "lucide-react";

export function FeaturesGrid() {
  return (
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
  );
}
