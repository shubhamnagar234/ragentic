"use client";

import { useWorkspaceStore } from "@/store/workspaceStore";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { sessionsApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Plus, MessageSquare, Trash2, Loader2 } from "lucide-react";
import { Session } from "@/types";
import { useEffect } from "react";

export default function ChatHistory() {
  const { id: workspaceId } = useParams() as { id: string };
  const queryClient = useQueryClient();
  const {
    sessions,
    setSessions,
    activeSessionId,
    setActiveSessionId,
  } = useWorkspaceStore();

  const { data: fetchedSessions, isLoading } = useQuery<Session[]>({
    queryKey: ["sessions", workspaceId],
    queryFn: () => sessionsApi.getAll(workspaceId),
  });

  useEffect(() => {
    if (fetchedSessions) {
      setSessions(fetchedSessions);
      if (!activeSessionId && fetchedSessions.length > 0) {
        setActiveSessionId(fetchedSessions[fetchedSessions.length - 1].id);
      }
    }
  }, [fetchedSessions, setSessions, activeSessionId, setActiveSessionId]);

  const createSessionMutation = useMutation({
    mutationFn: (title: string) => sessionsApi.create(workspaceId, title),
    onSuccess: (newSession: Session) => {
      queryClient.setQueryData(
        ["sessions", workspaceId],
        (old: Session[] | undefined) => [...(old || []), newSession]
      );
      setActiveSessionId(newSession.id);
    },
  });

  const deleteSessionMutation = useMutation({
    mutationFn: (sessionId: string) => sessionsApi.delete(workspaceId, sessionId),
    onSuccess: (_, deletedId) => {
      queryClient.setQueryData(
        ["sessions", workspaceId],
        (old: Session[] | undefined) =>
          old?.filter((s) => s.id !== deletedId) || []
      );
      if (activeSessionId === deletedId) {
        const remaining = sessions.filter(s => s.id !== deletedId);
        setActiveSessionId(remaining.length > 0 ? remaining[remaining.length - 1].id : null);
      }
    },
  });

  const handleNewChat = () => {
    createSessionMutation.mutate(`Chat ${sessions.length + 1}`);
  };

  return (
    <div className="border border-border rounded-xl p-3 space-y-2">
      <div className="flex items-center justify-between px-1 mb-1">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Chat History
        </p>
        <button
          onClick={handleNewChat}
          disabled={createSessionMutation.isPending}
          className="text-xs flex items-center gap-1 text-primary hover:text-primary/80"
        >
          {createSessionMutation.isPending ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <Plus className="w-3 h-3" />
          )}
          New
        </button>
      </div>

      <div className="space-y-1">
        {isLoading ? (
          <p className="text-xs text-muted-foreground px-1">Loading...</p>
        ) : sessions.length === 0 ? (
          <p className="text-xs text-muted-foreground px-1">No history yet</p>
        ) : (
          sessions.map((session) => {
            const isActive = activeSessionId === session.id;
            return (
              <div
                key={session.id}
                onClick={() => setActiveSessionId(session.id)}
                className={cn(
                  "group flex items-center justify-between px-2 py-1.5 rounded-lg transition-colors cursor-pointer",
                  isActive ? "bg-primary/10 text-primary" : "hover:bg-muted text-muted-foreground"
                )}
              >
                <div className="flex items-center gap-2 truncate">
                  <MessageSquare className="w-3.5 h-3.5 shrink-0" />
                  <span className="text-xs font-medium truncate">
                    {session.title}
                  </span>
                </div>
                {sessions.length > 1 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteSessionMutation.mutate(session.id);
                    }}
                    className={cn(
                      "opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-destructive/10 hover:text-destructive",
                      deleteSessionMutation.isPending && deleteSessionMutation.variables === session.id && "opacity-100"
                    )}
                  >
                    {deleteSessionMutation.isPending && deleteSessionMutation.variables === session.id ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <Trash2 className="w-3 h-3" />
                    )}
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
