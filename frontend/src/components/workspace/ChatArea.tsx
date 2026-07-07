"use client";

import { useState, useEffect, useRef } from "react";
import { useChatStore } from "@/store/chatStore";
import { Message, SourceCitation } from "@/types";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Bot,
  User,
  AlertCircle,
  Copy,
  CheckCircle,
  CheckCircle2,
  Trash2,
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { useQuery } from "@tanstack/react-query";
import { messagesApi } from "@/lib/api";

interface Props {
  workspaceId: string;
}

const confidenceConfig = {
  HIGH: {
    label: "High confidence",
    icon: CheckCircle,
    className: "text-green-600 bg-green-500/10",
  },
  MEDIUM: {
    label: "Medium confidence",
    icon: AlertCircle,
    className: "text-amber-600 bg-amber-500/10",
  },
  LOW: {
    label: "Low confidence — verify independently",
    icon: AlertCircle,
    className: "text-red-600 bg-red-500/10",
  },
};

function SourcesList({ sources }: { sources: SourceCitation[] }) {
  if (!sources.length) return null;

  return (
    <div className="mt-3 space-y-1">
      <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
        Sources · {sources.length} selected
      </p>
      {sources.map((source, i) => (
        <div
          key={i}
          className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-muted/50 border border-border"
        >
          <span className="text-[10px] text-muted-foreground w-4">{i + 1}</span>
          <span className="text-xs text-foreground flex-1 truncate">
            {source.text_preview}
          </span>
          <span className="text-[10px] font-medium text-green-600 bg-green-500/10 px-1.5 py-0.5 rounded-full">
            {source.score.toFixed(2)}
          </span>
        </div>
      ))}
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-muted flex-shrink-0 mt-1"
    >
      {copied ? (
        <CheckCircle2 className="w-3.5 h-3.5 text-green-600" />
      ) : (
        <Copy className="w-3.5 h-3.5 text-muted-foreground" />
      )}
    </button>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const confidence = message.confidence
    ? confidenceConfig[message.confidence]
    : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn("flex gap-3 items-start", isUser && "flex-row-reverse")}
    >
      <Avatar className="w-7 h-7 flex-shrink-0 mt-0.5">
        <AvatarFallback
          className={cn(
            "text-xs",
            isUser ? "bg-primary text-primary-foreground" : "bg-muted",
          )}
        >
          {isUser ? (
            <User className="w-3.5 h-3.5" />
          ) : (
            <Bot className="w-3.5 h-3.5" />
          )}
        </AvatarFallback>
      </Avatar>

      <div
        className={cn(
          "max-w-[80%] space-y-2",
          isUser && "items-end flex flex-col",
        )}
      >
        {/* Bubble + copy button */}
        <div className="flex items-start gap-1 group">
          <div
            className={cn(
              "px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed",
              isUser
                ? "bg-primary text-primary-foreground rounded-tr-sm"
                : "bg-muted rounded-tl-sm",
            )}
          >
            {message.content}
          </div>
          {!isUser && <CopyButton text={message.content} />}
        </div>

        {/* Confidence badge */}
        {confidence && (
          <div
            className={cn(
              "flex items-center gap-1.5 text-xs px-2 py-1 rounded-lg w-fit",
              confidence.className,
            )}
          >
            <confidence.icon className="w-3 h-3" />
            {confidence.label}
          </div>
        )}

        {/* Sources */}
        {message.sources && message.sources.length > 0 && (
          <SourcesList sources={message.sources} />
        )}
      </div>
    </motion.div>
  );
}

function StreamingBubble() {
  const { streamingMessage } = useChatStore();
  if (!streamingMessage) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex gap-3 items-start"
    >
      <Avatar className="w-7 h-7 flex-shrink-0 mt-0.5">
        <AvatarFallback className="text-xs bg-muted">
          <Bot className="w-3.5 h-3.5" />
        </AvatarFallback>
      </Avatar>

      <div className="max-w-[80%] space-y-2">
        <div className="px-3.5 py-2.5 rounded-2xl rounded-tl-sm text-sm leading-relaxed bg-muted">
          {streamingMessage.content || (
            <span className="flex gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:0ms]" />
              <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:150ms]" />
              <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:300ms]" />
            </span>
          )}
        </div>

        {/* Sources after streaming */}
        {!streamingMessage.isStreaming &&
          streamingMessage.sources.length > 0 && (
            <SourcesList sources={streamingMessage.sources} />
          )}
      </div>
    </motion.div>
  );
}

export default function ChatArea({ workspaceId }: Props) {
  const { messages, streamingMessage, setMessages, clearMessages, isLoading } =
    useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load message history on mount
  const { data: historicalMessages = [] } = useQuery<Message[]>({
    queryKey: ["messages", workspaceId],
    queryFn: () => messagesApi.getAll(workspaceId),
  });

  // Sync historical messages to store
  useEffect(() => {
    if (historicalMessages.length > 0 && messages.length === 0) {
      setMessages(historicalMessages);
    }
  }, [historicalMessages, messages.length, setMessages]);

  // Auto scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingMessage?.content]);

  return (
    <div className="flex-1 border border-border rounded-xl overflow-hidden flex flex-col min-h-0 bg-card">
      {/* Chat header */}
      {messages.length > 0 && (
        <div className="flex items-center justify-between px-4 py-2 border-b border-border">
          <span className="text-xs text-muted-foreground">
            {messages.length} messages
          </span>
          <button
            onClick={clearMessages}
            disabled={isLoading}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-destructive transition-colors disabled:opacity-50"
          >
            <Trash2 className="w-3 h-3" />
            Clear chat
          </button>
        </div>
      )}

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Empty state */}
        {messages.length === 0 && !streamingMessage && (
          <div className="h-full flex items-center justify-center">
            <div className="text-center space-y-2">
              <Bot className="w-10 h-10 text-muted-foreground mx-auto" />
              <p className="text-sm font-medium">Ask anything</p>
              <p className="text-xs text-muted-foreground">
                Paste a link or upload a file to get started
              </p>
            </div>
          </div>
        )}

        <AnimatePresence>
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
        </AnimatePresence>

        {streamingMessage && <StreamingBubble />}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
