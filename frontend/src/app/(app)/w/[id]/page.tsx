"use client";

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useWorkspaceStore } from "@/store/workspaceStore";
import { useChatStore } from "@/store/chatStore";
import { sourcesApi } from "@/lib/api";
import AgentSidebar from "@/components/workspace/AgentSidebar";
import ChatArea from "@/components/workspace/ChatArea";
import EvalPanel from "@/components/workspace/EvalPanel";
import Timeline from "@/components/workspace/Timeline";
import InputBar from "@/components/workspace/InputBar";

export default function WorkspaceChatPage() {
  const params = useParams();
  const id = params.id as string;
  const setSources = useWorkspaceStore((state) => state.setSources);

  // Fetch and poll sources to update the UI when ingestion completes
  const { data: sources } = useQuery({
    queryKey: ["sources", id],
    queryFn: () => sourcesApi.getAll(id),
    refetchInterval: 3000, // Poll every 3 seconds
  });

  useEffect(() => {
    if (sources) {
      setSources(sources);
    }
  }, [sources, setSources]);

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col gap-3">
      {/* Main content area */}
      <div className="flex-1 grid grid-cols-[220px_1fr_200px] gap-3 min-h-0">
        {/* Left — Agent sidebar */}
        <AgentSidebar />

        {/* Center — Chat */}
        <div className="flex flex-col gap-3 min-h-0">
          <ChatArea workspaceId={id} />
          <InputBar workspaceId={id} />
        </div>

        {/* Right — Eval panel */}
        <EvalPanel />
      </div>

      {/* Bottom — Timeline */}
      <Timeline />
    </div>
  );
}
