import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useChatStore } from "@/store/chatStore";
import { createChatStream } from "@/lib/api";
import { TimelineEvent, SourceCitation, ConfidenceLevel, Message } from "@/types";

export function useSSE() {
  const {
    startStreaming,
    stopStreaming,
    appendToken,
    setSources,
    setConfidence,
    addTimelineEvent,
    setActiveAgent,
    setIsLoading,
    clearTimeline,
    clearStreamingMessage,
  } = useChatStore();
  const queryClient = useQueryClient();

  const sendMessage = useCallback(
    async (workspaceId: string, query: string, sourceIds: string[] = []) => {
      setIsLoading(true);
      clearTimeline();
      startStreaming();

      try {
        const response = await createChatStream(workspaceId, query, sourceIds);

        if (!response.ok || !response.body) {
          throw new Error("Stream failed to start");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();

          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE events from buffer
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;

            const raw = line.slice(6).trim();
            if (!raw) continue;

            try {
              const event = JSON.parse(raw);

              switch (event.type) {
                case "timeline": {
                  const timelineEvent = event.data as TimelineEvent;
                  addTimelineEvent(timelineEvent);
                  setActiveAgent(timelineEvent.agent);
                  break;
                }

                case "token": {
                  appendToken(event.data as string);
                  break;
                }

                case "sources": {
                  setSources(event.data as SourceCitation[]);
                  break;
                }

                case "confidence": {
                  setConfidence(event.data as ConfidenceLevel);
                  break;
                }

                case "done": {
                  stopStreaming();
                  setActiveAgent(null);
                  setIsLoading(false);

                  // Optimistically add the AI message to prevent flicker
                  const state = useChatStore.getState();
                  if (state.streamingMessage) {
                    queryClient.setQueryData(["messages", workspaceId], (old: Message[] = []) => [
                      ...old,
                      {
                        id: `optimistic-${Date.now()}`,
                        workspace_id: workspaceId,
                        user_id: "",
                        role: "assistant",
                        content: state.streamingMessage!.content,
                        sources: state.streamingMessage!.sources,
                        confidence: state.streamingMessage!.confidence,
                        created_at: new Date().toISOString(),
                      },
                    ]);
                  }
                  
                  clearStreamingMessage();
                  queryClient.invalidateQueries({ queryKey: ["messages", workspaceId] });
                  break;
                }

                case "error": {
                  console.error("[SSE] Error:", event.data);
                  stopStreaming();
                  setIsLoading(false);
                  break;
                }
              }
            } catch (e) {
              console.error("[SSE] Failed to parse event:", raw, e);
            }
          }
        }
      } catch (error) {
        console.error("[SSE] Stream error:", error);
        stopStreaming();
      } finally {
        setIsLoading(false);
        setActiveAgent(null);
      }
    },
    [
      startStreaming,
      stopStreaming,
      appendToken,
      setSources,
      setConfidence,
      addTimelineEvent,
      setActiveAgent,
      setIsLoading,
      clearTimeline,
      clearStreamingMessage,
      queryClient,
    ],
  );

  return { sendMessage };
}
