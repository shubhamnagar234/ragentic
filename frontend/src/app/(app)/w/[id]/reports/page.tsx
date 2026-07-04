"use client";

import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { reportsApi } from "@/lib/api";
import { Report } from "@/types";
import { Button } from "@/components/ui/button";
import {
  Trash2,
  FileText,
  Download,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";
import { cn } from "@/lib/utils";

function ActionItemBadge({ priority }: { priority?: string }) {
  const config = {
    high: "bg-red-500/10 text-red-600",
    medium: "bg-amber-500/10 text-amber-600",
    low: "bg-green-500/10 text-green-600",
  };
  if (!priority) return null;
  return (
    <span
      className={cn(
        "text-[10px] px-2 py-0.5 rounded-full font-medium",
        config[priority as keyof typeof config] ??
          "bg-muted text-muted-foreground",
      )}
    >
      {priority}
    </span>
  );
}

function ReportCard({
  report,
  onDelete,
}: {
  report: Report;
  onDelete: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="border border-border rounded-xl bg-card overflow-hidden"
    >
      {/* Header */}
      <div className="p-4 flex items-start gap-3">
        <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
          <FileText className="w-4 h-4 text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-heading font-semibold text-sm">{report.title}</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            {new Date(report.created_at).toLocaleDateString("en-US", {
              year: "numeric",
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {report.pdf_url && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => window.open(report.pdf_url, "_blank")}
            >
              <Download className="w-4 h-4" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-destructive"
            onClick={() => onDelete(report.id)}
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-border pt-4">
          {/* Summary */}
          {report.summary && (
            <div>
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                Summary
              </h4>
              <p className="text-sm text-foreground leading-relaxed">
                {report.summary}
              </p>
            </div>
          )}

          {/* Action items */}
          {report.action_items && report.action_items.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                Action Items
              </h4>
              <div className="space-y-2">
                {report.action_items.map((item, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-2 p-2.5 rounded-lg bg-muted/50 border border-border"
                  >
                    <span className="text-xs text-muted-foreground w-4 shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm">{item.description}</p>
                      <div className="flex items-center gap-2 mt-1">
                        {item.owner && (
                          <span className="text-xs text-muted-foreground">
                            @{item.owner}
                          </span>
                        )}
                        {item.deadline && (
                          <span className="text-xs text-muted-foreground">
                            Due: {item.deadline}
                          </span>
                        )}
                        <ActionItemBadge priority={item.priority} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Open questions */}
          {report.open_questions && report.open_questions.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                Open Questions
              </h4>
              <ul className="space-y-1">
                {report.open_questions.map((q, i) => (
                  <li key={i} className="text-sm text-foreground flex gap-2">
                    <span className="text-muted-foreground">•</span>
                    {String(q)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}

export default function ReportsPage() {
  const params = useParams();
  const id = params.id as string;
  const queryClient = useQueryClient();

  const { data: reports = [], isLoading } = useQuery<Report[]>({
    queryKey: ["reports", id],
    queryFn: () => reportsApi.getAll(id),
  });

  const deleteMutation = useMutation({
    mutationFn: (reportId: string) => reportsApi.delete(id, reportId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reports", id] });
    },
  });

  return (
    <div className="max-w-3xl mx-auto py-6">
      <div className="mb-6">
        <h2 className="font-heading text-xl font-bold">Reports</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Generated meeting reports and summaries
        </p>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div
              key={i}
              className="h-20 rounded-xl border border-border bg-muted animate-pulse"
            />
          ))}
        </div>
      )}

      {!isLoading && reports.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 gap-3">
          <FileText className="w-10 h-10 text-muted-foreground" />
          <div className="text-center">
            <h3 className="font-heading font-semibold">No reports yet</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Ask RAGENTIC to generate a meeting report in the chat
            </p>
          </div>
        </div>
      )}

      {!isLoading && reports.length > 0 && (
        <div className="space-y-3">
          {reports.map((report) => (
            <ReportCard
              key={report.id}
              report={report}
              onDelete={(reportId) => deleteMutation.mutate(reportId)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
