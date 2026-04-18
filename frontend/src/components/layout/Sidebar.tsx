/**
 * Sidebar — minimal icon strip (collapsed) or full panel (expanded).
 *
 * Collapsed: 56px icon strip with logo, new chat, search, theme, settings
 * Expanded:  260px panel with conversation list, search, branding
 */

import { useEffect, useCallback, useState, useMemo } from "react";
import { useConversation, groupByDate } from "../../hooks/useConversation";
import { ThemeToggle } from "../ui/ThemeToggle";
import { useStore } from "../../store/useStore";
import { ConfirmModal } from "../ui/ConfirmModal";
import {
  IconPlus,
  IconTrash,
  IconMenu,
  IconClose,
  IconSearch,
  IconSparkles,
  IconMessageSquare,
  IconClock,
  IconSettings,
} from "../ui/icons";

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
        group relative flex items-center rounded-lg cursor-pointer
        transition-all duration-200
        ${
          isActive
            ? "bg-accent/20 border-l-2 border-l-accent pl-2.5"
            : "hover:bg-bg-elevated/80 pl-3 border-l-2 border-l-transparent"
        }
      `}
    >
      <button
        onClick={onSelect}
        className={`flex-1 text-left py-2.5 pr-8 text-sm truncate focus-ring rounded-lg ${
          isActive ? "text-white font-medium" : "text-[#A3A3A3]"
        }`}
      >
        {title}
      </button>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        className="
          absolute right-1.5 top-1/2 -translate-y-1/2
          opacity-0 group-hover:opacity-100
          text-text-muted hover:text-status-error
          p-1.5 rounded-md transition-all focus-ring
          hover:bg-status-error/10
        "
        aria-label={`Delete ${title}`}
      >
        <IconTrash size={13} />
      </button>
    </div>
  );
}

function SectionLabel({ label }: { label: string }): React.ReactElement {
  return (
    <div className="px-3 py-1.5 text-[11px] font-semibold text-[#737373] uppercase tracking-wider">
      {label}
    </div>
  );
}

function IconButton({
  icon: Icon,
  label,
  onClick,
  isActive,
  size = 18,
}: {
  icon: React.ComponentType<{ size?: number; className?: string }>;
  label: string;
  onClick: () => void;
  isActive?: boolean;
  size?: number;
}): React.ReactElement {
  return (
    <button
      onClick={onClick}
      className={`
        w-10 h-10 rounded-xl flex items-center justify-center
        transition-all duration-200 focus-ring
        ${isActive
          ? "bg-accent/15 text-accent"
          : "text-text-muted hover:text-text-primary hover:bg-bg-elevated"
        }
      `}
      aria-label={label}
      title={label}
    >
      <Icon size={size} />
    </button>
  );
}

export function Sidebar(): React.ReactElement {
  const sidebarOpen = useStore((s) => s.sidebarOpen);
  const { conversations, activeConversationId, createNew, switchTo, remove } =
    useConversation();

  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const filteredConversations = useMemo(() => {
    if (!searchQuery.trim()) return conversations;
    const q = searchQuery.toLowerCase();
    return conversations.filter((c) => c.title.toLowerCase().includes(q));
  }, [conversations, searchQuery]);

  const grouped = groupByDate(filteredConversations);

  // Listen for ⌘N custom event
  const handleNewConversation = useCallback(() => {
    createNew();
  }, [createNew]);

  useEffect(() => {
    window.addEventListener("ri:new-conversation", handleNewConversation);
    return () =>
      window.removeEventListener("ri:new-conversation", handleNewConversation);
  }, [handleNewConversation]);

  // ── Collapsed: minimal icon strip ─────────────────────────────
  if (!sidebarOpen) {
    return (
      <div className="w-[60px] flex-shrink-0 border-r border-[#333333] bg-bg-primary flex flex-col items-center py-4 gap-2">
        {/* Logo */}
        <div className="w-8 h-8 rounded-lg bg-[#FFFFFF] flex items-center justify-center mb-6">
          <IconSparkles size={16} className="text-[#111111]" />
        </div>

        {/* New chat */}
        <IconButton
          icon={IconPlus}
          label="New conversation"
          onClick={createNew}
        />

        {/* Search placeholder */}
        <IconButton
          icon={IconSearch}
          label="Search"
          onClick={() => useStore.getState().toggleSidebar()}
        />

        {/* Home/Chat history */}
        <IconButton
          icon={IconMessageSquare}
          label="Home"
          onClick={() => useStore.getState().toggleSidebar()}
          isActive={!!activeConversationId}
        />

        {/* Folder/Projects */}
        <IconButton
          icon={IconSettings} // Using settings as placeholder for folder
          label="Projects"
          onClick={() => useStore.getState().toggleSidebar()}
        />

        {/* Recent/Clock */}
        <IconButton
          icon={IconClock}
          label="Recent"
          onClick={() => useStore.getState().toggleSidebar()}
        />

        {/* Spacer */}
        <div className="flex-1" />

        {/* User profile avatar placeholder at bottom */}
        <div className="w-8 h-8 rounded-full bg-[#E5D3B3] flex items-center justify-center mt-auto cursor-pointer">
          <span className="text-xs font-medium text-[#111111]">UI</span>
        </div>
      </div>
    );
  }

  // ── Expanded: full sidebar ────────────────────────────────────
  return (
    <div className="w-sidebar flex-shrink-0 border-r border-[#333333] bg-bg-primary flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center">
            <IconSparkles size={16} className="text-black" />
          </div>
          <div className="flex flex-col">
            <span className="text-[13px] font-bold tracking-tight text-text-primary leading-tight">
              E-Commerce
            </span>
            <span className="text-[10px] font-semibold text-accent tracking-[0.15em] uppercase">
              Intelligence
            </span>
          </div>
        </div>
        <button
          onClick={() => useStore.getState().toggleSidebar()}
          className="text-text-muted hover:text-text-primary transition-colors focus-ring rounded-lg p-1.5 hover:bg-bg-elevated"
          aria-label="Close sidebar"
        >
          <IconClose size={16} />
        </button>
      </div>

      {/* New Conversation button */}
      <div className="px-3 mb-2">
        <button
          onClick={createNew}
          id="new-conversation-btn"
          className="
            w-full py-2.5 rounded-xl text-sm font-medium
            bg-accent/10 text-accent border border-accent/20
            hover:bg-accent/15 hover:border-accent/30
            transition-all duration-200 focus-ring
            flex items-center justify-center gap-2
          "
        >
          <IconPlus size={16} />
          New Conversation
        </button>
      </div>

      {/* Search */}
      <div className="px-3 mb-2">
        <div className="relative">
          <IconSearch size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversations..."
            className="
              w-full bg-[#212121] border border-[#333333] rounded-lg
              text-xs text-text-primary placeholder:text-text-muted
              pl-8 pr-3 py-2 outline-none
              focus:border-[#525252] focus:bg-[#262626]
              transition-all duration-200
            "
          />
        </div>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto py-1 px-2 space-y-0.5">
        {filteredConversations.length === 0 && (
          <div className="px-3 py-8 text-sm text-text-muted text-center">
            {searchQuery ? "No matches" : "No conversations yet"}
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
      <div className="border-t border-[#333333] px-5 py-4 flex items-center justify-between">
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
