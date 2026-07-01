"use client";

import { useParams } from "next/navigation";
import { useWorkspaceStore } from "@/store/workspaceStore";
import { useChatStore } from "@/store/chatStore";
import AgentSidebar from "@/components/workspace/AgentSidebar";
import ChatArea from "@/components/workspace/ChatArea";
import EvalPanel from "@/components/workspace/EvalPanel";
import Timeline from "@/components/workspace/Timeline";
import InputBar from "@/components/workspace/InputBar";

export default function WorkspaceChatPage() {
  const params = useParams();
  const id = params.id as string;

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
