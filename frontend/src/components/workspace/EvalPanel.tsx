"use client";

import { useChatStore } from "@/store/chatStore";
import { cn } from "@/lib/utils";
import { BarChart2, RefreshCw, Shield } from "lucide-react";

interface RetrieverMetadata {
  dense_count?: number;
  sparse_count?: number;
  reranked_count?: number;
}

interface CriticMetadata {
  faithfulness?: number;
  confidence_level?: string;
  needs_retry?: boolean;
}

export default function EvalPanel() {
  const { timelineEvents, streamingMessage, messages } = useChatStore();

  // Get latest eval scores from timeline events
  const criticEvents = timelineEvents.filter((e) => e.agent === "critic");
  const latestCritic = criticEvents[criticEvents.length - 1];

  const criticMeta = latestCritic?.metadata as CriticMetadata | undefined;
  const faithfulness = criticMeta?.faithfulness;
  const confidence = criticMeta?.confidence_level;
  const retryCount = timelineEvents.filter(
    (e) => e.agent === "rewriter",
  ).length;

  // Count sources used
  const sourcesUsed = streamingMessage?.sources.length ?? 0;

  const metrics = [
    {
      label: "Faithfulness",
      value: faithfulness != null ? `${(faithfulness * 100).toFixed(0)}%` : "—",
      icon: Shield,
      color:
        faithfulness == null
          ? "text-muted-foreground"
          : faithfulness >= 0.7
            ? "text-green-600"
            : "text-red-600",
    },
    {
      label: "Confidence",
      value: confidence ?? "—",
      icon: BarChart2,
      color:
        confidence === "HIGH"
          ? "text-green-600"
          : confidence === "MEDIUM"
            ? "text-amber-600"
            : confidence === "LOW"
              ? "text-red-600"
              : "text-muted-foreground",
    },
    {
      label: "Retries",
      value: retryCount.toString(),
      icon: RefreshCw,
      color: retryCount > 0 ? "text-amber-600" : "text-muted-foreground",
    },
    {
      label: "Sources",
      value: sourcesUsed.toString(),
      icon: BarChart2,
      color: "text-muted-foreground",
    },
  ];

  return (
    <div className="flex flex-col gap-3 overflow-y-auto">
      {/* Eval metrics */}
      <div className="border border-border rounded-xl p-3">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-1 mb-3">
          Evaluation
        </p>
        <div className="grid grid-cols-2 gap-2">
          {metrics.map((metric) => (
            <div
              key={metric.label}
              className="bg-muted/50 rounded-lg p-2.5 space-y-1"
            >
              <span
                className={cn(
                  "text-base font-semibold font-heading",
                  metric.color,
                )}
              >
                {metric.value}
              </span>
              <p className="text-[10px] text-muted-foreground">
                {metric.label}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Retrieval breakdown */}
      <div className="border border-border rounded-xl p-3">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-1 mb-3">
          Retrieval
        </p>
        {timelineEvents.length === 0 ? (
          <p className="text-xs text-muted-foreground px-1">No retrieval yet</p>
        ) : (
          <div className="space-y-2">
            {timelineEvents
              .filter((e) => e.agent === "retriever")
              .slice(-1)
              .map((event, i) => {
                const meta = event.metadata as RetrieverMetadata | undefined;
                return (
                  <div key={i} className="space-y-1.5">
                    {meta && (
                      <>
                        <div className="flex justify-between text-xs">
                          <span className="text-muted-foreground">Dense</span>
                          <span className="font-medium">
                            {meta.dense_count ?? 0}
                          </span>
                        </div>
                        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary rounded-full"
                            style={{
                              width: `${Math.min(100, ((meta.dense_count ?? 0) / 20) * 100)}%`,
                            }}
                          />
                        </div>
                        <div className="flex justify-between text-xs">
                          <span className="text-muted-foreground">BM25</span>
                          <span className="font-medium">
                            {meta.sparse_count ?? 0}
                          </span>
                        </div>
                        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-green-500 rounded-full"
                            style={{
                              width: `${Math.min(100, ((meta.sparse_count ?? 0) / 20) * 100)}%`,
                            }}
                          />
                        </div>
                        <div className="flex justify-between text-xs">
                          <span className="text-muted-foreground">
                            Selected
                          </span>
                          <span className="font-medium">
                            {meta.reranked_count ?? 0}
                          </span>
                        </div>
                        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-500 rounded-full"
                            style={{
                              width: `${Math.min(100, ((meta.reranked_count ?? 0) / 5) * 100)}%`,
                            }}
                          />
                        </div>
                      </>
                    )}
                  </div>
                );
              })}
          </div>
        )}
      </div>
    </div>
  );
}
