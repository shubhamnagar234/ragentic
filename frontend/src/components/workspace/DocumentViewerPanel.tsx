"use client";

import { useWorkspaceStore } from "@/store/workspaceStore";
import { X, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";

export default function DocumentViewerPanel() {
  const { activeCitation, setActiveCitation } = useWorkspaceStore();

  if (!activeCitation) return null;

  return (
    <div className="flex flex-col h-full bg-card border border-border rounded-xl overflow-hidden animate-in slide-in-from-right-4 duration-300">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-border bg-muted/30">
        <div className="flex items-center gap-2 overflow-hidden">
          <FileText className="w-4 h-4 text-primary shrink-0" />
          <h3 className="text-sm font-semibold truncate">
            {activeCitation.source_title || "Source Document"}
          </h3>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 rounded-full hover:bg-muted shrink-0 ml-2"
          onClick={() => setActiveCitation(null)}
        >
          <X className="w-4 h-4 text-muted-foreground" />
        </Button>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Score: {(activeCitation.score * 100).toFixed(1)}%</span>
            <span className="uppercase tracking-wider font-medium">
              {activeCitation.source_type || "UNKNOWN"}
            </span>
          </div>

          <div className="prose prose-sm dark:prose-invert max-w-none">
            <p className="text-sm leading-relaxed whitespace-pre-wrap font-medium">
              {activeCitation.full_text || activeCitation.text_preview}
            </p>
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
