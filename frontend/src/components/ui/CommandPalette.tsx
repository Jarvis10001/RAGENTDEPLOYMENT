/**
 * CommandPalette — global ⌘K overlay with fuzzy search.
 *
 * Sections: Recent Conversations, Quick Actions, Quick Prompts
 * Keyboard-navigable with ↑↓ arrows + Enter.
 * Rendered via createPortal to document.body.
 */

import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useStore } from "../../store/useStore";
import { useConversation } from "../../hooks/useConversation";
import {
  IconSearch,
  IconPlus,
  IconMessageSquare,
  IconSun,
  IconMoon,
  IconPanelRight,
  IconDownload,
  IconTarget,
  IconTrendingUp,
  IconBarChart,
  IconPackage,
  IconGlobe,
  IconSparkles,
} from "./icons";

// ── Types ────────────────────────────────────────────────────────

interface CommandItem {
  id: string;
  label: string;
  section: "conversations" | "actions" | "prompts";
  icon: React.ComponentType<{ size?: number; className?: string }>;
  iconColor?: string;
  shortcut?: string;
  onSelect: () => void;
}

// ── Quick prompts ────────────────────────────────────────────────

const QUICK_PROMPTS = [
  { text: "Why did net profit margin drop last month?", icon: IconTrendingUp, color: "text-red-400" },
  { text: "Which campaigns have the best ROI?", icon: IconTarget, color: "text-indigo-400" },
  { text: "Show revenue breakdown by campaign channel", icon: IconBarChart, color: "text-pink-400" },
  { text: "Compare freight costs across warehouses", icon: IconPackage, color: "text-amber-400" },
  { text: "How does our return rate compare to industry?", icon: IconGlobe, color: "text-cyan-400" },
];

// ── Component ────────────────────────────────────────────────────

export function CommandPalette(): React.ReactElement | null {
  const isOpen = useStore((s) => s.commandPaletteOpen);
  const setOpen = useStore((s) => s.setCommandPaletteOpen);
  const theme = useStore((s) => s.theme);
  const conversations = useStore((s) => s.conversations);

  const { createNew, switchTo, exportConversation } = useConversation();

  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Close helper
  const close = useCallback(() => {
    setOpen(false);
    setQuery("");
    setActiveIndex(0);
  }, [setOpen]);

  // Build command items
  const items = useMemo<CommandItem[]>(() => {
    const result: CommandItem[] = [];

    // Conversations (most recent 8)
    conversations.slice(0, 8).forEach((c) => {
      result.push({
        id: `conv-${c.id}`,
        label: c.title,
        section: "conversations",
        icon: IconMessageSquare,
        iconColor: "text-text-muted",
        onSelect: () => {
          switchTo(c.id);
          close();
        },
      });
    });

    // Quick actions
    result.push({
      id: "action-new",
      label: "New Conversation",
      section: "actions",
      icon: IconPlus,
      iconColor: "text-accent",
      shortcut: navigator.platform.includes("Mac") ? "⌘N" : "Ctrl+N",
      onSelect: () => {
        createNew();
        close();
      },
    });

    result.push({
      id: "action-theme",
      label: `Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`,
      section: "actions",
      icon: theme === "dark" ? IconSun : IconMoon,
      iconColor: "text-amber-400",
      onSelect: () => {
        useStore.getState().toggleTheme();
        close();
      },
    });

    result.push({
      id: "action-panel",
      label: "Toggle Analysis Panel",
      section: "actions",
      icon: IconPanelRight,
      iconColor: "text-text-secondary",
      onSelect: () => {
        useStore.getState().toggleRightPanel();
        close();
      },
    });

    result.push({
      id: "action-export",
      label: "Export Conversation",
      section: "actions",
      icon: IconDownload,
      iconColor: "text-emerald-400",
      onSelect: () => {
        exportConversation();
        close();
      },
    });

    // Quick prompts
    QUICK_PROMPTS.forEach((p, idx) => {
      result.push({
        id: `prompt-${idx}`,
        label: p.text,
        section: "prompts",
        icon: p.icon,
        iconColor: p.color,
        onSelect: () => {
          // Dispatch a send
          close();
          // Small delay so palette closes first
          setTimeout(() => {
            window.dispatchEvent(
              new CustomEvent("ri:command-send", { detail: p.text })
            );
          }, 100);
        },
      });
    });

    return result;
  }, [conversations, theme, switchTo, createNew, exportConversation, close]);

  // Filtered items
  const filtered = useMemo(() => {
    if (!query.trim()) return items;
    const q = query.toLowerCase();
    return items.filter((item) => item.label.toLowerCase().includes(q));
  }, [items, query]);

  // Group filtered items by section
  const grouped = useMemo(() => {
    const convs = filtered.filter((i) => i.section === "conversations");
    const actions = filtered.filter((i) => i.section === "actions");
    const prompts = filtered.filter((i) => i.section === "prompts");
    return { conversations: convs, actions, prompts };
  }, [filtered]);

  // Reset active index when filter changes
  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Scroll active item into view
  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    const active = list.querySelector("[data-active='true']");
    if (active) {
      active.scrollIntoView({ block: "nearest" });
    }
  }, [activeIndex]);

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setActiveIndex((prev) => Math.min(prev + 1, filtered.length - 1));
          break;
        case "ArrowUp":
          e.preventDefault();
          setActiveIndex((prev) => Math.max(prev - 1, 0));
          break;
        case "Enter":
          e.preventDefault();
          if (filtered[activeIndex]) {
            filtered[activeIndex].onSelect();
          }
          break;
        case "Escape":
          e.preventDefault();
          close();
          break;
      }
    },
    [filtered, activeIndex, close]
  );

  // Render section
  const renderSection = (
    label: string,
    sectionItems: CommandItem[],
    startIndex: number
  ) => {
    if (sectionItems.length === 0) return null;
    return (
      <div className="mb-1">
        <div className="px-3 py-1.5 text-[10px] font-semibold text-text-muted uppercase tracking-widest select-none">
          {label}
        </div>
        {sectionItems.map((item, idx) => {
          const globalIdx = startIndex + idx;
          const isActive = globalIdx === activeIndex;
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              data-active={isActive}
              onClick={item.onSelect}
              onMouseEnter={() => setActiveIndex(globalIdx)}
              className={`
                w-full flex items-center gap-3 px-3 py-2.5 text-left
                rounded-lg transition-colors duration-100
                ${isActive ? "bg-accent/10 text-text-primary" : "text-text-secondary hover:bg-bg-elevated"}
              `}
            >
              <div
                className={`
                  w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0
                  ${isActive ? "bg-accent/15" : "bg-bg-elevated"}
                `}
              >
                <Icon
                  size={14}
                  className={item.iconColor || "text-text-muted"}
                />
              </div>
              <span className="flex-1 text-sm truncate">{item.label}</span>
              {item.shortcut && (
                <kbd className="text-[10px] text-text-muted bg-bg-elevated border border-border/50 rounded px-1.5 py-0.5 font-mono select-none">
                  {item.shortcut}
                </kbd>
              )}
            </button>
          );
        })}
      </div>
    );
  };

  // Compute section start indices for global keyboard navigation
  const convStart = 0;
  const actionsStart = grouped.conversations.length;
  const promptsStart = actionsStart + grouped.actions.length;

  const modalContent = (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[9998] flex items-start justify-center pt-[15vh] p-4"
          onClick={close}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0, y: -10 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0, y: -10 }}
            transition={{ type: "spring", damping: 30, stiffness: 400 }}
            onClick={(e) => e.stopPropagation()}
            onKeyDown={handleKeyDown}
            className="w-full max-w-lg bg-bg-surface border border-border rounded-2xl shadow-2xl overflow-hidden"
          >
            {/* Search input */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-border/50">
              <IconSearch size={16} className="text-text-muted flex-shrink-0" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search commands, conversations..."
                className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-muted outline-none"
              />
              <kbd className="text-[10px] text-text-muted bg-bg-elevated border border-border/50 rounded px-1.5 py-0.5 font-mono select-none">
                ESC
              </kbd>
            </div>

            {/* Results list */}
            <div
              ref={listRef}
              className="max-h-[50vh] overflow-y-auto p-2"
            >
              {filtered.length === 0 ? (
                <div className="flex flex-col items-center py-10 text-center">
                  <IconSparkles
                    size={24}
                    className="text-text-muted/40 mb-2"
                  />
                  <p className="text-sm text-text-muted">No results found</p>
                  <p className="text-xs text-text-muted/60 mt-1">
                    Try a different search term
                  </p>
                </div>
              ) : (
                <>
                  {renderSection(
                    "Recent Conversations",
                    grouped.conversations,
                    convStart
                  )}
                  {renderSection(
                    "Quick Actions",
                    grouped.actions,
                    actionsStart
                  )}
                  {renderSection(
                    "Quick Prompts",
                    grouped.prompts,
                    promptsStart
                  )}
                </>
              )}
            </div>

            {/* Footer hints */}
            <div className="flex items-center gap-4 px-4 py-2.5 border-t border-border/50 bg-bg-elevated/50">
              <span className="flex items-center gap-1.5 text-[10px] text-text-muted select-none">
                <kbd className="bg-bg-elevated border border-border/50 rounded px-1 py-0.5 font-mono">↑↓</kbd>
                Navigate
              </span>
              <span className="flex items-center gap-1.5 text-[10px] text-text-muted select-none">
                <kbd className="bg-bg-elevated border border-border/50 rounded px-1 py-0.5 font-mono">↵</kbd>
                Select
              </span>
              <span className="flex items-center gap-1.5 text-[10px] text-text-muted select-none">
                <kbd className="bg-bg-elevated border border-border/50 rounded px-1 py-0.5 font-mono">esc</kbd>
                Close
              </span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );

  if (typeof window === "undefined") return null;

  return createPortal(modalContent, document.body);
}
