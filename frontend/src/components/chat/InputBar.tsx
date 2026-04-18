/**
 * InputBar — premium input area with animated gradient glow border,
 * auto-expanding textarea, character counter, and send/stop controls.
 * InputBar — premium input area with gradient glow border,
 * mode toggle (Fast / Thinking), icon send button, and stop streaming button.
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { IconSend, IconStop, IconZap, IconBrain } from "../ui/icons";
import { useStore, type ChatMode } from "../../store/useStore";

interface InputBarProps {
  onSend: (message: string) => void;
  isStreaming: boolean;
}

const MAX_HEIGHT = 192; // ~8 lines at leading-6

export function InputBar({ onSend, isStreaming }: InputBarProps): React.ReactElement {
  const [value, setValue] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const chatMode = useStore((s) => s.chatMode);
  const setChatMode = useStore((s) => s.setChatMode);

  // Auto-resize textarea
  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_HEIGHT)}px`;
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

  const toggleMode = useCallback(() => {
    setChatMode(chatMode === "fast" ? "thinking" : "fast");
  }, [chatMode, setChatMode]);

  const canSend = value.trim().length > 0 && !isStreaming;
  const charCount = value.length;

  return (
    <div className="flex-shrink-0 border-t border-border bg-bg-primary/80 backdrop-blur-sm px-4 py-3">
      <div className="max-w-4xl mx-auto">
        {/* Outer glow wrapper */}
        <motion.div
          className="relative rounded-2xl"
          animate={{
            boxShadow: isFocused
              ? "0 0 0 1px rgba(99, 102, 241, 0.4), 0 0 24px rgba(99, 102, 241, 0.12), 0 0 48px rgba(139, 92, 246, 0.06)"
              : "0 0 0 0px transparent, 0 0 0px transparent, 0 0 0px transparent",
          }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        >
          {/* Gradient border overlay — visible on focus */}
          <motion.div
            className="absolute -inset-[1px] rounded-2xl pointer-events-none"
            style={{
              background: "linear-gradient(135deg, #6366F1, #8B5CF6, #A78BFA, #6366F1)",
              backgroundSize: "300% 300%",
            }}
            animate={{
              opacity: isFocused ? 1 : 0,
              backgroundPosition: isFocused ? ["0% 50%", "100% 50%", "0% 50%"] : "0% 50%",
            }}
            transition={{
              opacity: { duration: 0.3 },
              backgroundPosition: { duration: 4, repeat: Infinity, ease: "linear" },
            }}
          />

          {/* Inner container (sits on top of gradient border) */}
          <div
            className={`
              relative flex items-end gap-2 rounded-2xl
              bg-bg-surface
              px-4 py-2.5
              transition-colors duration-300
              ${!isFocused ? "border border-border" : "border border-transparent"}
              ${isStreaming ? "border-accent/20" : ""}
            `}
          >
            {/* Mode toggle pill */}
            <button
              id="mode-toggle"
              onClick={toggleMode}
              disabled={isStreaming}
              className={`
                flex-shrink-0 flex items-center gap-1.5
                px-2.5 py-1.5 rounded-lg
                text-2xs font-medium
                transition-all duration-250 ease-out
                disabled:opacity-40 disabled:cursor-not-allowed
                select-none cursor-pointer
                ${chatMode === "thinking"
                  ? "bg-purple-500/15 text-purple-400 border border-purple-500/30 hover:bg-purple-500/25"
                  : "bg-accent/10 text-accent border border-accent/20 hover:bg-accent/20"
                }
              `}
              title={chatMode === "thinking"
                ? "Thinking mode — deeper analysis with Gemini 2.5 Flash"
                : "Fast mode — quick answers with Gemini Flash Lite"
              }
              aria-label={`Switch to ${chatMode === "fast" ? "thinking" : "fast"} mode`}
            >
              <AnimatePresence mode="wait">
                {chatMode === "thinking" ? (
                  <motion.span
                    key="thinking"
                    initial={{ scale: 0.6, opacity: 0, rotate: -90 }}
                    animate={{ scale: 1, opacity: 1, rotate: 0 }}
                    exit={{ scale: 0.6, opacity: 0, rotate: 90 }}
                    transition={{ duration: 0.2 }}
                    className="flex items-center gap-1.5"
                  >
                    <IconBrain size={13} />
                    <span>Thinking</span>
                  </motion.span>
                ) : (
                  <motion.span
                    key="fast"
                    initial={{ scale: 0.6, opacity: 0, rotate: 90 }}
                    animate={{ scale: 1, opacity: 1, rotate: 0 }}
                    exit={{ scale: 0.6, opacity: 0, rotate: -90 }}
                    transition={{ duration: 0.2 }}
                    className="flex items-center gap-1.5"
                  >
                    <IconZap size={13} />
                    <span>Fast</span>
                  </motion.span>
                )}
              </AnimatePresence>
            </button>

            <textarea
              ref={textareaRef}
              id="chat-input"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={handleKeyDown}
<<<<<<< HEAD
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder="Ask about your revenue, campaigns, or customers..."
=======
              placeholder={
                chatMode === "thinking"
                  ? "Ask a complex question for deeper analysis..."
                  : "Ask about your revenue, campaigns, or customers..."
              }
>>>>>>> bb199f2367bdff62a9e63335519d0ee05c0e64d9
              disabled={isStreaming}
              rows={1}
              className="
                flex-1 bg-transparent text-sm text-text-primary
                placeholder:text-text-muted
                outline-none resize-none
                py-1 leading-6
                disabled:opacity-50
                max-h-48
              "
              style={{ overflowY: "auto" }}
            />

            {/* Bottom-row meta: character count + keyboard hint */}
            <div className="flex items-center gap-2 pb-1.5 flex-shrink-0">
              {/* Character counter — appears after 50 chars */}
              <AnimatePresence>
                {charCount > 50 && (
                  <motion.span
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    transition={{ duration: 0.15 }}
                    className="text-[10px] text-text-muted/50 tabular-nums select-none"
                  >
                    {charCount}
                  </motion.span>
                )}
              </AnimatePresence>

              {/* Keyboard hint */}
              <span className="text-2xs text-text-muted whitespace-nowrap hidden sm:block select-none">
                {navigator.platform.includes("Mac") ? "⌘" : "Ctrl"} ↵
              </span>
            </div>

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
                    ${canSend
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
        </motion.div>
      </div>
    </div>
  );
}
