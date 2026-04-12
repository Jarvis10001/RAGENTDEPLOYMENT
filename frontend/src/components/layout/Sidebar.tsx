/**
 * Sidebar — 240px collapsible left panel.
 *
 * - App name "E-commerce Intelligence Agent" at top
 * - Conversation history grouped by Today/Yesterday/Older
 * - Bottom: New Conversation, Settings, Theme toggle
 */

import { useEffect, useCallback } from "react";
import { useConversation, groupByDate } from "../../hooks/useConversation";
import { ThemeToggle } from "../ui/ThemeToggle";
import { useStore } from "../../store/useStore";
import { ConfirmModal } from "../ui/ConfirmModal";
import { useState } from "react";

function ConversationItem({
  id,
  title,
  isActive,
  onSelect,
  onDelete,
}: {
  id: string;
  title: string;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
}): React.ReactElement {
  return (
    <div
      className={`
        group relative flex items-center rounded-input cursor-pointer
        transition-colors
        ${
          isActive
            ? "bg-accent/10 border-l-2 border-l-accent pl-2.5"
            : "hover:bg-bg-elevated pl-3 border-l-2 border-l-transparent"
        }
      `}
    >
      <button
        onClick={onSelect}
        className="flex-1 text-left py-2 pr-8 text-sm text-text-primary truncate focus-ring rounded-input"
      >
        {title}
      </button>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        className="
          absolute right-1 top-1/2 -translate-y-1/2
          opacity-0 group-hover:opacity-100
          text-2xs text-text-muted hover:text-status-error
          px-1.5 py-1 rounded transition-all focus-ring
        "
        aria-label={`Delete ${title}`}
      >
        Delete
      </button>
    </div>
  );
}

function SectionLabel({ label }: { label: string }): React.ReactElement {
  return (
    <div className="px-3 py-1.5 text-2xs font-medium text-text-muted uppercase tracking-wider">
      {label}
    </div>
  );
}

export function Sidebar(): React.ReactElement {
  const sidebarOpen = useStore((s) => s.sidebarOpen);
  const { conversations, activeConversationId, createNew, switchTo, remove } =
    useConversation();

  const [deletingId, setDeletingId] = useState<string | null>(null);

  const grouped = groupByDate(conversations);

  // Listen for ⌘N custom event
  const handleNewConversation = useCallback(() => {
    createNew();
  }, [createNew]);

  useEffect(() => {
    window.addEventListener("ri:new-conversation", handleNewConversation);
    return () =>
      window.removeEventListener("ri:new-conversation", handleNewConversation);
  }, [handleNewConversation]);

  if (!sidebarOpen) {
    return (
      <div className="w-12 flex-shrink-0 border-r border-border bg-bg-surface flex flex-col items-center py-4 gap-3">
        <button
          onClick={() => useStore.getState().toggleSidebar()}
          className="text-2xs text-text-muted hover:text-text-primary transition-colors focus-ring rounded p-1"
          aria-label="Open sidebar"
        >
          Menu
        </button>
      </div>
    );
  }

  return (
    <div className="w-sidebar flex-shrink-0 border-r border-border bg-bg-surface flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-5 py-5 flex items-start justify-between border-b border-border/40 bg-bg-primary/20">
        <div className="flex flex-col">
          <span className="text-[15px] font-bold tracking-tight text-text-primary">
            E-Commerce
          </span>
          <span className="text-[10px] font-bold text-accent tracking-[0.2em] uppercase mt-0.5">
            Intelligence Agent
          </span>
        </div>
        <button
          onClick={() => useStore.getState().toggleSidebar()}
          className="text-2xs text-text-muted hover:text-text-primary transition-colors focus-ring rounded p-1 mt-0.5"
          aria-label="Close sidebar"
        >
          Close
        </button>
      </div>

      {/* Divider */}
      <div className="mx-4 border-b border-border" />

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto py-2 px-2 space-y-0.5">
        {conversations.length === 0 && (
          <div className="px-3 py-8 text-sm text-text-muted text-center">
            No conversations yet
          </div>
        )}

        {grouped.today.length > 0 && (
          <div>
            <SectionLabel label="Today" />
            {grouped.today.map((c) => (
              <ConversationItem
                key={c.id}
                id={c.id}
                title={c.title}
                isActive={c.id === activeConversationId}
                onSelect={() => switchTo(c.id)}
                onDelete={() => setDeletingId(c.id)}
              />
            ))}
          </div>
        )}

        {grouped.yesterday.length > 0 && (
          <div className="mt-2">
            <SectionLabel label="Yesterday" />
            {grouped.yesterday.map((c) => (
              <ConversationItem
                key={c.id}
                id={c.id}
                title={c.title}
                isActive={c.id === activeConversationId}
                onSelect={() => switchTo(c.id)}
                onDelete={() => setDeletingId(c.id)}
              />
            ))}
          </div>
        )}

        {grouped.older.length > 0 && (
          <div className="mt-2">
            <SectionLabel label="Older" />
            {grouped.older.map((c) => (
              <ConversationItem
                key={c.id}
                id={c.id}
                title={c.title}
                isActive={c.id === activeConversationId}
                onSelect={() => switchTo(c.id)}
                onDelete={() => setDeletingId(c.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Bottom section */}
      <div className="border-t border-border px-3 py-3 space-y-2">
        <button
          onClick={createNew}
          id="new-conversation-btn"
          className="
            w-full py-2 rounded-input text-sm font-medium
            border border-border text-text-primary
            hover:border-accent hover:text-accent
            transition-colors focus-ring
          "
        >
          New Conversation
        </button>

        <button
          className="
            w-full py-1.5 rounded-input text-sm text-text-secondary
            hover:bg-bg-elevated transition-colors text-left px-2
            focus-ring
          "
        >
          Settings
        </button>

        <ThemeToggle />
      </div>

      <ConfirmModal
        isOpen={deletingId !== null}
        title="Delete Conversation"
        message="Are you sure you want to delete this conversation? This action cannot be undone."
        onCancel={() => setDeletingId(null)}
        onConfirm={() => {
          if (deletingId) {
            remove(deletingId);
            setDeletingId(null);
          }
        }}
      />
    </div>
  );
}
