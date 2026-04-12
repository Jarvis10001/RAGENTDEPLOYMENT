/**
 * InputBar — fixed-bottom input area.
 *
 * Full-width pill shape, auto-expands up to 5 lines.
 * "Send" text button in accent color, ⌘ Enter hint.
 */

import { useState, useCallback, useRef, useEffect } from "react";

interface InputBarProps {
  onSend: (message: string) => void;
  isStreaming: boolean;
}

export function InputBar({ onSend, isStreaming }: InputBarProps): React.ReactElement {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    const maxHeight = 5 * 24; // ~5 lines
    textarea.style.height = `${Math.min(textarea.scrollHeight, maxHeight)}px`;
  }, []);

  useEffect(() => {
    adjustHeight();
  }, [value, adjustHeight]);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setValue("");
    // Reset height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, isStreaming, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // ⌘ Enter or Ctrl+Enter to send
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  return (
    <div className="flex-shrink-0 border-t border-border bg-bg-primary px-4 py-3">
      <div className="max-w-4xl mx-auto">
        <div
          className="
            flex items-end gap-3 rounded-pill
            border border-border bg-bg-surface
            px-5 py-2.5
            focus-within:border-accent/50
            transition-colors
            shadow-accent
          "
        >
          <textarea
            ref={textareaRef}
            id="chat-input"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your revenue, campaigns, or customers..."
            disabled={isStreaming}
            rows={1}
            className="
              flex-1 bg-transparent text-sm text-text-primary
              placeholder:text-text-muted
              outline-none resize-none
              py-1 leading-6
              disabled:opacity-50
            "
          />

          {/* Keyboard hint */}
          <span className="text-2xs text-text-muted whitespace-nowrap pb-1 hidden sm:block select-none">
            {navigator.platform.includes("Mac") ? "⌘" : "Ctrl"} Enter
          </span>

          {/* Send button */}
          <button
            onClick={handleSend}
            disabled={!value.trim() || isStreaming}
            className="
              text-sm font-medium text-accent
              hover:text-accent-hover
              disabled:text-text-muted disabled:cursor-not-allowed
              transition-colors focus-ring rounded
              pb-0.5 whitespace-nowrap
            "
          >
            {isStreaming ? "Sending..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}
