/**
 * MessageList — scrollable message area.
 *
 * Renders messages top to bottom (newest at bottom).
 * Smooth auto-scroll on new messages.
 * Shows EmptyState when no conversation is active or empty.
 */

import { useEffect, useRef } from "react";
import { useStore } from "../../store/useStore";
import { MessageItem } from "./MessageItem";
import { EmptyState } from "./EmptyState";

interface MessageListProps {
  onSelectQuestion: (question: string) => void;
}

export function MessageList({
  onSelectQuestion,
}: MessageListProps): React.ReactElement {
  const activeConversationId = useStore((s) => s.activeConversationId);
  const conversations = useStore((s) => s.conversations);
  const isStreaming = useStore((s) => s.isStreaming);

  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const activeConversation = conversations.find(
    (c) => c.id === activeConversationId
  );
  const messages = activeConversation?.messages || [];

  // Auto-scroll to bottom only when a new message is added
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages.length]);

  // No conversation or empty conversation
  if (!activeConversationId || messages.length === 0) {
    return <EmptyState onSelectQuestion={onSelectQuestion} />;
  }

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto px-6 md:px-12 lg:px-12 py-6"
    >
      <div className="max-w-4xl mx-auto">
        {messages.map((msg) => (
          <MessageItem key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} className="h-1" />
      </div>
    </div>
  );
}
