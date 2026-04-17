/**
 * InputBar — premium input area with gradient glow border,
 * icon send button, and stop streaming button.
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { IconSend, IconStop } from "../ui/icons";

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

  const canSend = value.trim().length > 0 && !isStreaming;

  return (
    <div className="flex-shrink-0 border-t border-border bg-bg-primary/80 backdrop-blur-sm px-4 py-3">
      <div className="max-w-4xl mx-auto">
        <div className="gradient-border rounded-2xl">
          <div
            className={`
              flex items-end gap-2 rounded-2xl
              border border-border bg-bg-surface
              px-4 py-2.5
              focus-within:border-accent/40
              transition-all duration-300
              ${isStreaming ? "border-accent/20" : ""}
            `}
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
            <span className="text-2xs text-text-muted whitespace-nowrap pb-1.5 hidden sm:block select-none">
              {navigator.platform.includes("Mac") ? "⌘" : "Ctrl"} ↵
            </span>

            {/* Send / Stop button */}
            <AnimatePresence mode="wait">
              {isStreaming ? (
                <motion.button
                  key="stop"
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.8, opacity: 0 }}
                  transition={{ duration: 0.15 }}
                  onClick={() => {
                    // Dispatch abort via custom event
                    window.dispatchEvent(new CustomEvent("ri:cancel-stream"));
                  }}
                  className="
                    flex-shrink-0 w-8 h-8 rounded-lg
                    flex items-center justify-center
                    bg-status-error/10 text-status-error
                    hover:bg-status-error/20
                    transition-colors focus-ring
                  "
                  aria-label="Stop generating"
                >
                  <IconStop size={16} />
                </motion.button>
              ) : (
                <motion.button
                  key="send"
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.8, opacity: 0 }}
                  transition={{ duration: 0.15 }}
                  onClick={handleSend}
                  disabled={!canSend}
                  className={`
                    flex-shrink-0 w-8 h-8 rounded-lg
                    flex items-center justify-center
                    transition-all duration-200 focus-ring
                    ${
                      canSend
                        ? "bg-accent text-white hover:bg-accent-hover shadow-accent"
                        : "bg-bg-elevated text-text-muted cursor-not-allowed"
                    }
                  `}
                  aria-label="Send message"
                >
                  <IconSend size={16} />
                </motion.button>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}
