/**
 * Sidebar — 260px collapsible left panel with glassmorphism.
 *
 * - Brand header with animated gradient dot
 * - Search/filter input
 * - Conversation history grouped by Today/Yesterday/Older
 * - Fluid Framer Motion layout animations on list items
 * - Bottom: New Conversation button + theme/settings icons
 */

import { useEffect, useCallback, useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useConversation, groupByDate } from "../../hooks/useConversation";
import { ThemeToggle } from "../ui/ThemeToggle";
import { useStore } from "../../store/useStore";
import { ConfirmModal } from "../ui/ConfirmModal";
import { IconPlus, IconTrash, IconMenu, IconClose, IconSearch, IconSparkles } from "../ui/icons";

const itemVariants = {
  initial: { opacity: 0, x: -12, scale: 0.95 },
  animate: { opacity: 1, x: 0, scale: 1 },
  exit: { opacity: 0, x: -12, scale: 0.95, transition: { duration: 0.2 } },
};

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
    <motion.div
      layout
      variants={itemVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ type: "spring", stiffness: 500, damping: 35, mass: 0.8 }}
      className={`
        group relative flex items-center rounded-lg cursor-pointer
        transition-colors duration-200
        ${
          isActive
            ? "bg-accent/10 border-l-2 border-l-accent pl-2.5"
            : "hover:bg-bg-elevated/80 pl-3 border-l-2 border-l-transparent"
        }
      `}
    >
      <button
        onClick={onSelect}
        className="flex-1 text-left py-2.5 pr-8 text-sm text-text-primary truncate focus-ring rounded-lg"
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
    </motion.div>
  );
}

function SectionLabel({ label }: { label: string }): React.ReactElement {
  return (
    <motion.div
      layout
      className="px-3 py-1.5 text-2xs font-semibold text-text-muted uppercase tracking-wider"
    >
      {label}
    </motion.div>
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

  if (!sidebarOpen) {
    return (
      <div className="w-12 flex-shrink-0 border-r border-border bg-bg-surface/50 flex flex-col items-center py-4 gap-3">
        <button
          onClick={() => useStore.getState().toggleSidebar()}
          className="text-text-muted hover:text-text-primary transition-colors focus-ring rounded-lg p-1.5 hover:bg-bg-elevated"
          aria-label="Open sidebar"
        >
          <IconMenu size={18} />
        </button>
      </div>
    );
  }

  return (
    <div className="w-sidebar flex-shrink-0 border-r border-border bg-bg-surface/50 backdrop-blur-sm flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
            <IconSparkles size={16} className="text-accent" />
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
              w-full bg-bg-elevated/50 border border-border/50 rounded-lg
              text-xs text-text-primary placeholder:text-text-muted
              pl-8 pr-3 py-2 outline-none
              focus:border-accent/30 focus:bg-bg-elevated
              transition-all duration-200
            "
          />
        </div>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto py-1 px-2 space-y-0.5">
        {filteredConversations.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="px-3 py-8 text-sm text-text-muted text-center"
          >
            {searchQuery ? "No matches" : "No conversations yet"}
          </motion.div>
        )}

        <AnimatePresence mode="popLayout">
          {grouped.today.length > 0 && (
            <motion.div layout key="section-today">
              <SectionLabel label="Today" />
              <AnimatePresence mode="popLayout">
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
              </AnimatePresence>
            </motion.div>
          )}

          {grouped.yesterday.length > 0 && (
            <motion.div layout key="section-yesterday" className="mt-2">
              <SectionLabel label="Yesterday" />
              <AnimatePresence mode="popLayout">
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
              </AnimatePresence>
            </motion.div>
          )}

          {grouped.older.length > 0 && (
            <motion.div layout key="section-older" className="mt-2">
              <SectionLabel label="Older" />
              <AnimatePresence mode="popLayout">
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
              </AnimatePresence>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Bottom section */}
      <div className="border-t border-border/40 px-3 py-3 flex items-center justify-between">
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
