"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "@/lib/api";
import { AnalyticsData, ScoreTrend } from "@/types";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  BarChart2,
  Brain,
  RefreshCw,
  Shield,
  Zap,
  Database,
} from "lucide-react";
import { cn } from "@/lib/utils";

function MetricCard({
  label,
  value,
  icon: Icon,
  color,
  description,
}: {
  label: string;
  value: string;
  icon: React.ElementType;
  color: string;
  description?: string;
}) {
  return (
    <div className="border border-border rounded-xl p-4 bg-card">
      <div className="flex items-center justify-between mb-3">
        <div
          className={cn(
            "w-8 h-8 rounded-lg flex items-center justify-center",
            color,
          )}
        >
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="font-heading text-2xl font-bold">{value}</div>
      <div className="text-sm font-medium mt-1">{label}</div>
      {description && (
        <div className="text-xs text-muted-foreground mt-0.5">
          {description}
        </div>
      )}
    </div>
  );
}

export default function AnalyticsPage() {
  const params = useParams();
  const id = params.id as string;

  const { data: metrics, isLoading: metricsLoading } = useQuery<AnalyticsData>({
    queryKey: ["analytics", id],
    queryFn: () => analyticsApi.getMetrics(id),
  });

  const { data: trendData, isLoading: trendLoading } = useQuery<{
    scores: ScoreTrend[];
  }>({
    queryKey: ["analytics-scores", id],
    queryFn: () => analyticsApi.getScoreTrend(id),
  });

  const scores = trendData?.scores ?? [];

  const chartData = scores.map((s, i) => ({
    query: `Q${i + 1}`,
    faithfulness:
      s.faithfulness != null ? Math.round(s.faithfulness * 100) : null,
    context_precision:
      s.context_precision != null
        ? Math.round(s.context_precision * 100)
        : null,
    answer_relevance:
      s.answer_relevance != null ? Math.round(s.answer_relevance * 100) : null,
  }));

  return (
    <div className="max-w-5xl mx-auto py-6 space-y-6">
      <div>
        <h2 className="font-heading text-xl font-bold">Analytics</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Retrieval quality and system performance metrics
        </p>
      </div>

      {/* Metrics grid */}
      {metricsLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="h-28 rounded-xl border border-border bg-muted animate-pulse"
            />
          ))}
        </div>
      ) : metrics ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <MetricCard
            label="Total queries"
            value={metrics.query_count.toString()}
            icon={Brain}
            color="bg-primary/10 text-primary"
          />
          <MetricCard
            label="Avg faithfulness"
            value={`${(metrics.avg_faithfulness * 100).toFixed(0)}%`}
            icon={Shield}
            color={
              metrics.avg_faithfulness >= 0.7
                ? "bg-green-500/10 text-green-600"
                : "bg-amber-500/10 text-amber-600"
            }
            description="How grounded answers are in context"
          />
          <MetricCard
            label="Hallucination rate"
            value={`${(metrics.hallucination_rate * 100).toFixed(0)}%`}
            icon={Zap}
            color={
              metrics.hallucination_rate <= 0.1
                ? "bg-green-500/10 text-green-600"
                : "bg-red-500/10 text-red-600"
            }
            description="1 - avg faithfulness score"
          />
          <MetricCard
            label="Retry rate"
            value={`${(metrics.retry_rate * 100).toFixed(0)}%`}
            icon={RefreshCw}
            color={
              metrics.retry_rate <= 0.2
                ? "bg-green-500/10 text-green-600"
                : "bg-amber-500/10 text-amber-600"
            }
            description="Queries that triggered self-healing"
          />
          <MetricCard
            label="Avg context precision"
            value={`${(metrics.avg_context_precision * 100).toFixed(0)}%`}
            icon={BarChart2}
            color="bg-blue-500/10 text-blue-600"
            description="Relevance of retrieved chunks"
          />
          <MetricCard
            label="Sources ingested"
            value={metrics.source_count.toString()}
            icon={Database}
            color="bg-purple-500/10 text-purple-600"
          />
        </div>
      ) : null}

      {/* RAGAS score trend chart */}
      <div className="border border-border rounded-xl p-5 bg-card">
        <h3 className="font-heading font-semibold text-sm mb-1">
          RAGAS Score Trend
        </h3>
        <p className="text-xs text-muted-foreground mb-5">
          Retrieval quality over time — faithfulness, precision, relevance
        </p>

        {trendLoading ? (
          <div className="h-48 bg-muted animate-pulse rounded-lg" />
        ) : chartData.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-sm text-muted-foreground">
            No evaluation data yet — ask questions to generate scores
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                dataKey="query"
                tick={{ fontSize: 11 }}
                className="text-muted-foreground"
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => `${v}%`}
                className="text-muted-foreground"
              />
              <Tooltip
                formatter={(value) => [`${value}%`]}
                contentStyle={{
                  backgroundColor: "var(--color-card)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
              />
              <Legend wrapperStyle={{ fontSize: "12px" }} />
              <Line
                type="monotone"
                dataKey="faithfulness"
                stroke="#22c55e"
                strokeWidth={2}
                dot={{ r: 3 }}
                connectNulls
                name="Faithfulness"
              />
              <Line
                type="monotone"
                dataKey="context_precision"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ r: 3 }}
                connectNulls
                name="Context Precision"
              />
              <Line
                type="monotone"
                dataKey="answer_relevance"
                stroke="#f59e0b"
                strokeWidth={2}
                dot={{ r: 3 }}
                connectNulls
                name="Answer Relevance"
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
