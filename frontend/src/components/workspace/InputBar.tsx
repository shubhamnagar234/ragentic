"use client";

import { useState, useRef } from "react";
import { useWorkspaceStore } from "@/store/workspaceStore";
import { useChatStore } from "@/store/chatStore";
import { useSSE } from "@/hooks/useSSE";
import { sourcesApi } from "@/lib/api";
import { detectSourceType } from "@/lib/detector";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
  Send,
  Paperclip,
  Link,
  Play,
  GitBranch,
  Globe,
  Loader2,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

interface Props {
  workspaceId: string;
}

const sourceIcons: Record<string, React.ElementType> = {
  YOUTUBE: Play,
  GITHUB: GitBranch,
  WEB: Globe,
  LOOM: Globe,
  PDF: Paperclip,
  AUDIO: Paperclip,
  VIDEO: Paperclip,
};

export default function InputBar({ workspaceId }: Props) {
  const [input, setInput] = useState("");
  const [detectedType, setDetectedType] = useState<string | null>(null);
  const [isIngesting, setIsIngesting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const { activeSourceIds } = useWorkspaceStore();
  const { isLoading } = useChatStore();
  const { sendMessage } = useSSE();

  const isUrl = (text: string) => {
    try {
      new URL(text.trim());
      return true;
    } catch {
      return false;
    }
  };

  const handleInputChange = (value: string) => {
    setInput(value);
    if (isUrl(value.trim())) {
      const type = detectSourceType(value.trim());
      setDetectedType(type);
    } else {
      setDetectedType(null);
    }
  };

  const handleIngestUrl = async () => {
    if (!input.trim() || !detectedType) return;
    setIsIngesting(true);
    try {
      await sourcesApi.create(workspaceId, {
        url: input.trim(),
        source_type: detectedType,
      });
      queryClient.invalidateQueries({ queryKey: ["sources", workspaceId] });
      setInput("");
      setDetectedType(null);
    } catch (e) {
      console.error("Ingestion failed:", e);
    } finally {
      setIsIngesting(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    // If it's a URL — ingest it
    if (detectedType) {
      await handleIngestUrl();
      return;
    }

    // Otherwise send as chat query
    const query = input.trim();
    setInput("");
    await sendMessage(workspaceId, query, activeSourceIds);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const DetectedIcon = detectedType
    ? (sourceIcons[detectedType] ?? Link)
    : null;

  return (
    <div className="border border-border rounded-xl bg-card p-3 space-y-2">
      {/* URL detection preview */}
      {detectedType && (
        <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-primary/5 border border-primary/20">
          {DetectedIcon && (
            <DetectedIcon className="w-3.5 h-3.5 text-primary flex-shrink-0" />
          )}
          <span className="text-xs text-primary font-medium">
            {detectedType} detected — press Enter to ingest
          </span>
          {isIngesting && (
            <Loader2 className="w-3 h-3 text-primary animate-spin ml-auto" />
          )}
        </div>
      )}

      {/* Input area */}
      <div className="flex gap-2 items-end">
        <Textarea
          value={input}
          onChange={(e) => handleInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything or paste a URL to ingest..."
          className="min-h-[44px] max-h-32 resize-none border-0 bg-transparent p-0 focus-visible:ring-0 text-sm"
          disabled={isLoading || isIngesting}
          rows={1}
        />

        <div className="flex items-center gap-1.5 flex-shrink-0">
          {/* File upload */}
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".pdf,.mp3,.mp4,.m4a,.wav,.mov"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              // File upload handled separately
              console.log("File selected:", file.name);
            }}
          />
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading || isIngesting}
          >
            <Paperclip className="w-4 h-4" />
          </Button>

          {/* Send button */}
          <Button
            size="icon"
            className="h-8 w-8"
            onClick={handleSend}
            disabled={!input.trim() || isLoading || isIngesting}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
