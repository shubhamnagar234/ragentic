"use client";

import { useChatStore } from "@/store/chatStore";
import { TimelineEvent } from "@/types";
import { cn } from "@/lib/utils";
import {
  CheckCircle,
  RefreshCw,
  AlertCircle,
  Clock,
  Loader2,
} from "lucide-react";

interface TimelineMetadata {
  faithfulness?: number;
  needs_retry?: boolean;
  confidence_level?: string;
  dense_count?: number;
  sparse_count?: number;
  reranked_count?: number;
}

const statusConfig = {
  active: {
    icon: Loader2,
    className: "text-blue-600",
    dotClassName: "bg-blue-500",
    spin: true,
  },
  completed: {
    icon: CheckCircle,
    className: "text-green-600",
    dotClassName: "bg-green-500",
    spin: false,
  },
  retrying: {
    icon: RefreshCw,
    className: "text-amber-600",
    dotClassName: "bg-amber-500",
    spin: false,
  },
  failed: {
    icon: AlertCircle,
    className: "text-red-600",
    dotClassName: "bg-red-500",
    spin: false,
  },
};

function TimelineRow({ event }: { event: TimelineEvent }) {
  const config = statusConfig[event.status] ?? statusConfig.completed;
  const Icon = config.icon;
  const meta = event.metadata as TimelineMetadata | undefined;

  const time = new Date(event.timestamp).toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <div className="flex items-center gap-3">
      <span className="text-[10px] text-muted-foreground font-mono w-16 flex-shrink-0">
        {time}
      </span>
      <div
        className={cn(
          "w-1.5 h-1.5 rounded-full flex-shrink-0",
          config.dotClassName,
        )}
      />
      <span className="text-xs text-foreground flex-1 truncate">
        {event.message}
      </span>

      {meta?.faithfulness != null && (
        <span
          className={cn(
            "text-[10px] px-1.5 py-0.5 rounded-full font-medium flex-shrink-0",
            meta.faithfulness >= 0.7
              ? "bg-green-500/10 text-green-600"
              : "bg-red-500/10 text-red-600",
          )}
        >
          faithfulness {(meta.faithfulness * 100).toFixed(0)}%
        </span>
      )}

      {meta?.needs_retry && (
        <span className="text-[10px] px-1.5 py-0.5 rounded-full font-medium bg-amber-500/10 text-amber-600 flex-shrink-0">
          retry triggered
        </span>
      )}

      <Icon
        className={cn(
          "w-3 h-3 flex-shrink-0",
          config.className,
          config.spin && "animate-spin",
        )}
      />
    </div>
  );
}

export default function Timeline() {
  const { timelineEvents } = useChatStore();

  return (
    <div className="border border-border rounded-xl bg-card px-4 py-3">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
        Self-healing timeline
      </p>

      {timelineEvents.length === 0 ? (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Clock className="w-3.5 h-3.5" />
          <span>Agent events will appear here during processing</span>
        </div>
      ) : (
        <div className="space-y-1.5">
          {timelineEvents.map((event, i) => (
            <TimelineRow key={i} event={event} />
          ))}
        </div>
      )}
    </div>
  );
}
