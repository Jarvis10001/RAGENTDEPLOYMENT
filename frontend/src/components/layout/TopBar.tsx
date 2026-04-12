/**
 * TopBar — 48px top bar with conversation title, Export, source pills, and panels toggle.
 */

import { useState, useCallback } from "react";
import { useStore } from "../../store/useStore";
import { useConversation } from "../../hooks/useConversation";

export function TopBar(): React.ReactElement {
  const activeConversationId = useStore((s) => s.activeConversationId);
  const conversations = useStore((s) => s.conversations);
  const lastToolsUsed = useStore((s) => s.lastToolsUsed);
  const rightPanelOpen = useStore((s) => s.rightPanelOpen);
  const sidebarOpen = useStore((s) => s.sidebarOpen);
  const toggleRightPanel = useStore((s) => s.toggleRightPanel);
  const toggleSidebar = useStore((s) => s.toggleSidebar);

  const { rename, exportConversation } = useConversation();

  const activeConversation = conversations.find(
    (c) => c.id === activeConversationId
  );
  const title = activeConversation?.title || "E-commerce Intelligence Agent";

  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(title);

  const handleDoubleClick = useCallback(() => {
    if (!activeConversationId) return;
    setEditValue(title);
    setIsEditing(true);
  }, [activeConversationId, title]);

  const handleBlur = useCallback(() => {
    setIsEditing(false);
    if (activeConversationId && editValue.trim()) {
      rename(activeConversationId, editValue.trim());
    }
  }, [activeConversationId, editValue, rename]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        handleBlur();
      }
      if (e.key === "Escape") {
        setIsEditing(false);
      }
    },
    [handleBlur]
  );

  return (
    <div className="h-topbar flex-shrink-0 border-b border-border bg-bg-surface flex items-center px-4 gap-3">


      {/* Conversation title */}
      <div className="flex-1 min-w-0">
        {isEditing ? (
          <input
            autoFocus
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={handleBlur}
            onKeyDown={handleKeyDown}
            className="
              w-full max-w-md bg-transparent border-b border-accent
              text-sm font-medium text-text-primary
              outline-none py-0.5
            "
          />
        ) : (
          <span
            onDoubleClick={handleDoubleClick}
            className="text-sm font-medium text-text-primary truncate block cursor-default"
            title="Double-click to edit"
          >
            {title}
          </span>
        )}
      </div>

      {/* Source indicator pills */}
      <div className="flex items-center gap-1.5">
        {lastToolsUsed.map((tool) => (
          <span
            key={tool}
            className="
              px-2 py-0.5 rounded-pill text-2xs font-medium
              bg-accent/10 text-accent border border-accent/20
            "
          >
            {tool}
          </span>
        ))}
      </div>

      {/* Export button */}
      {activeConversationId && (
        <button
          onClick={exportConversation}
          className="text-sm text-text-secondary hover:text-text-primary transition-colors focus-ring rounded px-2 py-1"
        >
          Export
        </button>
      )}

      {/* Right panel toggle */}
      <button
        onClick={toggleRightPanel}
        className={`
          text-sm px-2 py-1 rounded-input transition-colors focus-ring
          ${
            rightPanelOpen
              ? "text-accent bg-accent/10"
              : "text-text-secondary hover:text-text-primary"
          }
        `}
      >
        Details
      </button>
    </div>
  );
}
