/**
 * InputBar — premium input area with animated glowing border during streaming,
 * mode toggle (Fast / Thinking), and send/stop buttons.
 *
 * When the agent is streaming, a revolving conic-gradient border
 * animates around the chat box (the "energy" effect).
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { IconSend, IconStop, IconZap, IconBrain, IconPlusCircle, IconImage } from "../ui/icons";
import { useStore, type ChatMode } from "../../store/useStore";

interface InputBarProps {
  onSend: (message: string) => void;
  isStreaming: boolean;
}

export function InputBar({ onSend, isStreaming }: InputBarProps): React.ReactElement {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const chatMode = useStore((s) => s.chatMode);
  const setChatMode = useStore((s) => s.setChatMode);

  // Auto-resize textarea
  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    const maxHeight = 6 * 24; // ~6 lines
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
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, isStreaming, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
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

  return (
    <div className="flex-shrink-0 px-4 py-4">
      <div className="max-w-3xl mx-auto">
        {/* Animated glow wrapper — activates with .is-glowing when streaming */}
        <div
          className={`input-glow-wrapper ${isStreaming ? "is-glowing" : ""}`}
        >
          <div
            className={`
              flex flex-col
              rounded-2xl
              border border-[#333333] bg-[#212121]
              backdrop-blur-sm
              transition-all duration-300
              ${isStreaming ? "border-transparent" : "focus-within:border-accent/30"}
            `}
          >
            {/* Textarea row */}
            <div className="flex items-end gap-2 px-4 pt-3 pb-1">
              <textarea
                ref={textareaRef}
                id="chat-input"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  chatMode === "thinking"
                    ? "Ask a complex question for deeper analysis..."
                    : "Ask whatever you want..."
                }
                disabled={isStreaming}
                rows={1}
                className="
                  flex-1 bg-transparent text-sm text-text-primary
                  placeholder:text-text-muted
                  outline-none resize-none
                  py-1.5 leading-6 min-h-[36px]
                  disabled:opacity-50
                "
              />
            </div>

            {/* Bottom toolbar row */}
            <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
              {/* Left side: mode toggle and attachments */}
              <div className="flex items-center">
                <button
                  id="mode-toggle"
                  onClick={toggleMode}
                  disabled={isStreaming}
                  className={`
                    flex items-center gap-1.5
                    px-2.5 py-1.5 rounded-lg
                    text-2xs font-medium
                    transition-all duration-250 ease-out
                    disabled:opacity-40 disabled:cursor-not-allowed
                    select-none cursor-pointer
                    ${chatMode === "thinking"
                      ? "bg-purple-500/15 text-purple-400 border border-purple-500/25 hover:bg-purple-500/25"
                      : "bg-accent/10 text-accent border border-accent/15 hover:bg-accent/20"
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

                <div className="flex items-center gap-3 ml-3 border-l border-[#333333] pl-3">
                  <button
                    type="button"
                    className="flex items-center gap-1.5 text-xs text-[#737373] hover:text-[#A3A3A3] transition-colors focus-ring rounded"
                  >
                    <IconPlusCircle size={14} />
                    <span>Add Attachment</span>
                  </button>
                  <button
                    type="button"
                    className="flex items-center gap-1.5 text-xs text-[#737373] hover:text-[#A3A3A3] transition-colors focus-ring rounded"
                  >
                    <IconImage size={14} />
                    <span>Use Image</span>
                  </button>
                </div>
              </div>

              {/* Right side: keyboard hint + counters + send/stop */}
              <div className="flex items-center gap-3">
                <span className="text-xs text-[#737373] select-none tabular-nums">
                  0/1000
                </span>
                <div className="w-px h-3 bg-[#333333] hidden sm:block"></div>
                <span className="text-2xs text-[#737373] whitespace-nowrap hidden sm:block select-none tracking-wider uppercase">
                  {navigator.platform.includes("Mac") ? "⌘" : "Ctrl"} ↵
                </span>

                <AnimatePresence mode="wait">
                  {isStreaming ? (
                    <motion.button
                      key="stop"
                      initial={{ scale: 0.8, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      exit={{ scale: 0.8, opacity: 0 }}
                      transition={{ duration: 0.15 }}
                      onClick={() => {
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
                            ? "bg-white text-[#111111] hover:bg-gray-200 shadow-md"
                            : "bg-[#111111] text-text-muted cursor-not-allowed border border-[#333333]"
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
      </div>
    </div>
  );
}
