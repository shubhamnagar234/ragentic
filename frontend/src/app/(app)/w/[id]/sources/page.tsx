"use client";

import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { sourcesApi } from "@/lib/api";
import { Source, SourceStatus } from "@/types";
import { useWorkspaceStore } from "@/store/workspaceStore";
import { useEffect } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Trash2,
  RefreshCw,
  CheckCircle,
  Clock,
  AlertCircle,
  Loader2,
  Play,
  Globe,
  GitBranch,
  Paperclip,
  Database,
} from "lucide-react";
import { motion } from "motion/react";
import { toast } from "sonner";

const sourceTypeIcons: Record<string, React.ElementType> = {
  YOUTUBE: Play,
  LOOM: Play,
  GITHUB: GitBranch,
  WEB: Globe,
  PDF: Paperclip,
  AUDIO: Paperclip,
  VIDEO: Play,
};

const statusConfig: Record<
  SourceStatus,
  {
    icon: React.ElementType;
    label: string;
    className: string;
  }
> = {
  queued: {
    icon: Clock,
    label: "Queued",
    className: "text-muted-foreground bg-muted",
  },
  ingesting: {
    icon: Loader2,
    label: "Ingesting",
    className: "text-blue-600 bg-blue-500/10",
  },
  ready: {
    icon: CheckCircle,
    label: "Ready",
    className: "text-green-600 bg-green-500/10",
  },
  degraded: {
    icon: AlertCircle,
    label: "Degraded",
    className: "text-amber-600 bg-amber-500/10",
  },
  "re-indexing": {
    icon: RefreshCw,
    label: "Re-indexing",
    className: "text-blue-600 bg-blue-500/10",
  },
  failed: {
    icon: AlertCircle,
    label: "Failed",
    className: "text-red-600 bg-red-500/10",
  },
};

function SourceCard({
  source,
  onDelete,
}: {
  source: Source;
  onDelete: (id: string) => void;
}) {
  const Icon = sourceTypeIcons[source.source_type] ?? Database;
  const status = statusConfig[source.status] ?? statusConfig.queued;
  const StatusIcon = status.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="border border-border rounded-xl p-4 bg-card hover:border-primary/30 transition-colors"
    >
      <div className="flex items-start gap-3">
        {/* Source type icon */}
        <div className="w-9 h-9 rounded-lg bg-muted flex items-center justify-center shrink-0">
          <Icon className="w-4 h-4 text-muted-foreground" />
        </div>

        {/* Source info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-medium text-sm truncate">
              {source.title ?? source.url ?? source.source_type}
            </h3>
            <span
              className={cn(
                "flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-medium shrink-0",
                status.className,
              )}
            >
              <StatusIcon
                className={cn(
                  "w-3 h-3",
                  source.status === "ingesting" && "animate-spin",
                )}
              />
              {status.label}
            </span>
          </div>

          {source.url && (
            <p className="text-xs text-muted-foreground truncate mb-2">
              {source.url}
            </p>
          )}

          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span>{source.source_type}</span>
            {source.chunk_count > 0 && <span>{source.chunk_count} chunks</span>}
            <span>{new Date(source.created_at).toLocaleDateString()}</span>
          </div>
        </div>

        {/* Delete button */}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground hover:text-destructive shrink-0"
          onClick={() => onDelete(source.id)}
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>
    </motion.div>
  );
}

export default function SourcesPage() {
  const params = useParams();
  const id = params.id as string;
  const queryClient = useQueryClient();
  const { setSources } = useWorkspaceStore();

  const { data: sources = [], isLoading } = useQuery<Source[]>({
    queryKey: ["sources", id],
    queryFn: () => sourcesApi.getAll(id),
    refetchInterval: 5000, // Poll every 5s to catch status updates
  });

  // Sync sources to store for sidebar filter
  useEffect(() => {
    setSources(sources);
  }, [sources, setSources]);

  const deleteMutation = useMutation({
    mutationFn: (sourceId: string) => sourcesApi.delete(id, sourceId),
    onSuccess: () => {
      toast.success("Source deleted");
      queryClient.invalidateQueries({ queryKey: ["sources", id] });
    },
    onError: () => toast.error("Failed to delete source"),
  });

  return (
    <div className="max-w-3xl mx-auto py-6">
      <div className="mb-6">
        <h2 className="font-heading text-xl font-bold">Sources</h2>
        <p className="text-sm text-muted-foreground mt-1">
          All ingested sources in this workspace
        </p>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-20 rounded-xl border border-border bg-muted animate-pulse"
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && sources.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 gap-3">
          <Database className="w-10 h-10 text-muted-foreground" />
          <div className="text-center">
            <h3 className="font-heading font-semibold">No sources yet</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Go to Chat and paste a URL or upload a file
            </p>
          </div>
        </div>
      )}

      {/* Sources list */}
      {!isLoading && sources.length > 0 && (
        <div className="space-y-3">
          {sources.map((source) => (
            <SourceCard
              key={source.id}
              source={source}
              onDelete={(sourceId) => deleteMutation.mutate(sourceId)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
