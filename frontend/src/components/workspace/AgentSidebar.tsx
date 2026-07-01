"use client";

import { useChatStore } from "@/store/chatStore";
import { useWorkspaceStore } from "@/store/workspaceStore";
import { cn } from "@/lib/utils";
import {
  Brain,
  Search,
  Shield,
  RefreshCw,
  MessageSquare,
  FileText,
  Layers,
} from "lucide-react";

const agents = [
  { id: "classifier", label: "Query analyzer", icon: Brain },
  { id: "retriever", label: "Retriever", icon: Search },
  { id: "critic", label: "Critic", icon: Shield },
  { id: "rewriter", label: "Query rewriter", icon: RefreshCw },
  { id: "responder", label: "Responder", icon: MessageSquare },
  { id: "reporter", label: "Report agent", icon: FileText },
];

const statusConfig = {
  active: {
    label: "Active",
    className: "bg-blue-500/10 text-blue-600 border-blue-200",
  },
  completed: {
    label: "Done",
    className: "bg-green-500/10 text-green-600 border-green-200",
  },
  retrying: {
    label: "Retried",
    className: "bg-amber-500/10 text-amber-600 border-amber-200",
  },
  failed: {
    label: "Failed",
    className: "bg-red-500/10 text-red-600 border-red-200",
  },
};

export default function AgentSidebar() {
  const { activeAgent, timelineEvents } = useChatStore();
  const { sources, activeSourceIds, toggleSourceFilter, clearSourceFilter } =
    useWorkspaceStore();

  // Determine agent status from timeline events
  const getAgentStatus = (agentId: string) => {
    const events = timelineEvents.filter((e) => e.agent === agentId);
    if (events.length === 0) return null;
    const last = events[events.length - 1];
    return last.status;
  };

  return (
    <div className="flex flex-col gap-4 overflow-y-auto">
      {/* Agents */}
      <div className="border border-border rounded-xl p-3 space-y-1">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-1 mb-2">
          Agents
        </p>
        {agents.map((agent) => {
          const status = getAgentStatus(agent.id);
          const isActive = activeAgent === agent.id;
          const config = status ? statusConfig[status] : null;

          return (
            <div
              key={agent.id}
              className={cn(
                "flex items-center gap-2.5 px-2 py-2 rounded-lg transition-colors",
                isActive && "bg-primary/5",
              )}
            >
              <div
                className={cn(
                  "w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0",
                  isActive ? "bg-primary/10" : "bg-muted",
                )}
              >
                <agent.icon
                  className={cn(
                    "w-3.5 h-3.5",
                    isActive ? "text-primary" : "text-muted-foreground",
                  )}
                />
              </div>
              <span className="text-xs font-medium flex-1 truncate">
                {agent.label}
              </span>
              {config && (
                <span
                  className={cn(
                    "text-[10px] px-1.5 py-0.5 rounded-full border font-medium",
                    config.className,
                  )}
                >
                  {config.label}
                </span>
              )}
              {isActive && !status && (
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
              )}
            </div>
          );
        })}
      </div>

      {/* Source filters */}
      <div className="border border-border rounded-xl p-3 space-y-1">
        <div className="flex items-center justify-between px-1 mb-2">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Sources
          </p>
          {activeSourceIds.length > 0 && (
            <button
              onClick={clearSourceFilter}
              className="text-[10px] text-muted-foreground hover:text-foreground"
            >
              Clear
            </button>
          )}
        </div>
        {sources.length === 0 ? (
          <p className="text-xs text-muted-foreground px-1">No sources yet</p>
        ) : (
          sources.map((source) => {
            const isActive =
              activeSourceIds.length === 0 ||
              activeSourceIds.includes(source.id);

            return (
              <button
                key={source.id}
                onClick={() => toggleSourceFilter(source.id)}
                className={cn(
                  "w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left transition-colors",
                  isActive
                    ? "bg-primary/5 text-foreground"
                    : "text-muted-foreground hover:bg-muted",
                )}
              >
                <Layers className="w-3 h-3 flex-shrink-0" />
                <span className="text-xs truncate">
                  {source.title ?? source.url ?? source.source_type}
                </span>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
