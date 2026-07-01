import { create } from "zustand";
import {
  Message,
  TimelineEvent,
  SourceCitation,
  ConfidenceLevel,
} from "@/types";

interface StreamingMessage {
  content: string;
  sources: SourceCitation[];
  confidence: ConfidenceLevel | null;
  isStreaming: boolean;
}

interface ChatStore {
  // Messages
  messages: Message[];
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  clearMessages: () => void;

  // Streaming state
  streamingMessage: StreamingMessage | null;
  appendToken: (token: string) => void;
  setSources: (sources: SourceCitation[]) => void;
  setConfidence: (confidence: ConfidenceLevel) => void;
  startStreaming: () => void;
  stopStreaming: () => void;

  // Timeline events
  timelineEvents: TimelineEvent[];
  addTimelineEvent: (event: TimelineEvent) => void;
  clearTimeline: () => void;

  // Agent status
  activeAgent: string | null;
  setActiveAgent: (agent: string | null) => void;

  // Loading
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;

  // Query
  query: string;
  setQuery: (query: string) => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  // Messages
  messages: [],
  setMessages: (messages) => set({ messages }),
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  clearMessages: () => set({ messages: [] }),

  // Streaming state
  streamingMessage: null,
  appendToken: (token) =>
    set((state) => ({
      streamingMessage: state.streamingMessage
        ? {
            ...state.streamingMessage,
            content: state.streamingMessage.content + token,
          }
        : {
            content: token,
            sources: [],
            confidence: null,
            isStreaming: true,
          },
    })),
  setSources: (sources) =>
    set((state) => ({
      streamingMessage: state.streamingMessage
        ? { ...state.streamingMessage, sources }
        : null,
    })),
  setConfidence: (confidence) =>
    set((state) => ({
      streamingMessage: state.streamingMessage
        ? { ...state.streamingMessage, confidence }
        : null,
    })),
  startStreaming: () =>
    set({
      streamingMessage: {
        content: "",
        sources: [],
        confidence: null,
        isStreaming: true,
      },
    }),
  stopStreaming: () =>
    set((state) => ({
      streamingMessage: state.streamingMessage
        ? { ...state.streamingMessage, isStreaming: false }
        : null,
    })),

  // Timeline events
  timelineEvents: [],
  addTimelineEvent: (event) =>
    set((state) => ({
      timelineEvents: [...state.timelineEvents, event],
    })),
  clearTimeline: () => set({ timelineEvents: [] }),

  // Agent status
  activeAgent: null,
  setActiveAgent: (agent) => set({ activeAgent: agent }),

  // Loading
  isLoading: false,
  setIsLoading: (loading) => set({ isLoading: loading }),

  // Query
  query: "",
  setQuery: (query) => set({ query }),
}));
