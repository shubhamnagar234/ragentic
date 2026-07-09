"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useWorkspaceStore } from "@/store/workspaceStore";
import { useEffect } from "react";
import { sourcesApi } from "@/lib/api";
import { Source } from "@/types";
import AgentSidebar from "@/components/workspace/AgentSidebar";
import ChatArea from "@/components/workspace/ChatArea";
import EvalPanel from "@/components/workspace/EvalPanel";
import Timeline from "@/components/workspace/Timeline";
import InputBar from "@/components/workspace/InputBar";

export default function WorkspaceChatPage() {
  const params = useParams();
  const id = params.id as string;
  const { setSources } = useWorkspaceStore();

  // Load sources into sidebar
  const { data: sources } = useQuery<Source[]>({
    queryKey: ["sources", id],
    queryFn: () => sourcesApi.getAll(id),
    refetchInterval: (query) => {
      const data = query.state.data as Source[] | undefined;
      const hasProcessing = data?.some(s => s.status === "queued" || s.status === "ingesting");
      return hasProcessing ? 2000 : 10000;
    },
  });

  useEffect(() => {
    if (sources) {
      setSources(sources);
    }
  }, [sources, setSources]);

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col gap-3">
      <div className="flex-1 grid grid-cols-[220px_1fr_200px] gap-3 min-h-0">
        <AgentSidebar />
        <div className="flex flex-col gap-3 min-h-0 min-w-0">
          <ChatArea workspaceId={id} />
          <InputBar workspaceId={id} />
        </div>
        <EvalPanel />
      </div>
      <Timeline />
    </div>
  );
}
