/**
 * MessageItem — renders a single user or assistant message.
 *
 * User: right-aligned with subtle avatar
 * Assistant: left-aligned with bot avatar, inline chart, copy button
 */

import { memo, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import { useStore, type Message } from "../../store/useStore";
import { CodeBlock } from "../ui/CodeBlock";
import { ChartRenderer } from "../charts/ChartRenderer";
import { IconBot, IconCopy, IconCheck, IconChevronDown, IconRefresh } from "../ui/icons";

interface MessageItemProps {
  message: Message;
}

// Custom components for ReactMarkdown
const markdownComponents: Components = {
  code({ className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || "");
    const codeString = String(children).replace(/\n$/, "");

    // Block code (has language class or is inside pre)
    if (match || (className && className.includes("language-"))) {
      return (
        <CodeBlock language={match?.[1]}>
          {codeString}
        </CodeBlock>
      );
    }

    // Check if this is a fenced code block (multi-line)
    if (codeString.includes("\n")) {
      return <CodeBlock>{codeString}</CodeBlock>;
    }

    // Inline code
    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  },
  // Remove the wrapper p tags from single-line content
  p({ children }) {
    return <p>{children}</p>;
  },
};

function MessageItemInner({ message }: MessageItemProps): React.ReactElement {
  const [showThinking, setShowThinking] = useState(false);
  const [copied, setCopied] = useState(false);
  const liveToolCalls = useStore((s) => s.toolCalls);
  const liveChartSpec = useStore((s) => s.currentChartSpec);

  const activeToolCalls = message.isStreaming ? liveToolCalls : message.toolCalls;
  const hasToolCalls = activeToolCalls && activeToolCalls.length > 0;

  // Chart: live spec during streaming, persisted spec for past messages
  const chartSpec = message.isStreaming ? liveChartSpec : message.chartSpec;

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(message.content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [message.content]);

  // Error message
  if (message.isError) {
    return (
      <div className="my-3 p-4 rounded-xl border border-status-error/20 bg-status-error/5">
        <p className="text-sm text-status-error/80">{message.content}</p>
        <button
          className="mt-2 text-sm text-accent hover:text-accent-hover transition-colors focus-ring rounded inline-flex items-center gap-1.5"
          onClick={() => {
            window.dispatchEvent(new CustomEvent("ri:retry"));
          }}
        >
          <IconRefresh size={14} />
          Retry
        </button>
      </div>
    );
  }

  // User message
  if (message.role === "user") {
    return (
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="my-4 flex justify-end gap-3"
      >
        <div className="max-w-[75%]">
          <div className="bg-accent/10 border border-accent/15 rounded-2xl rounded-tr-md px-4 py-2.5">
            <p className="text-sm text-text-primary leading-relaxed">
              {message.content}
            </p>
          </div>
          <p className="text-[10px] text-text-muted text-right mt-1 pr-1 select-none">
            {new Date(message.timestamp).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        </div>
      </motion.div>
    );
  }

  // Assistant message
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="my-4 group/msg"
    >
      <div className="flex gap-3">
        {/* Bot avatar */}
        <div className="flex-shrink-0 mt-1">
          <div className="w-7 h-7 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
            <IconBot size={14} className="text-accent" />
          </div>
        </div>

        <div className="flex-1 min-w-0">
          {/* Detailed Thinking block */}
          {hasToolCalls && (
            <div className="mb-3">
              <button
                onClick={() => setShowThinking((v) => !v)}
                className="flex items-center gap-2 text-2xs text-text-muted hover:text-text-secondary transition-colors focus-ring px-2.5 py-1.5 rounded-lg border border-border/50 bg-bg-surface hover:bg-bg-elevated"
              >
                <IconChevronDown
                  size={12}
                  className={`transition-transform duration-200 ${showThinking ? "rotate-180" : ""}`}
                />
                <span className="font-medium">
                  {showThinking ? "Hide" : "Show"} reasoning
                </span>
                <span className="tabular-nums text-text-muted/70">
                  {activeToolCalls.length} step{activeToolCalls.length !== 1 ? "s" : ""}
                </span>
              </button>

              <AnimatePresence>
                {showThinking && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden mt-2"
                  >
                    <div className="p-3 bg-bg-elevated/60 rounded-xl border border-border/40 text-xs space-y-3">
                      {activeToolCalls.map((tc, idx) => (
                        <div key={idx} className="border-l-2 border-accent/30 pl-3">
                          <div className="font-semibold text-text-primary mb-0.5 text-[11px]">
                            {tc.tool.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                          </div>
                          <div className="text-text-muted line-clamp-2 font-mono text-[10px] break-all">
                            {tc.input}
                          </div>
                        </div>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}

          {/* Inline chart */}
          {chartSpec && !message.isStreaming && (
            <ChartRenderer spec={chartSpec} showDataCard={true} />
          )}

          {/* Message content */}
          <div
            className={`prose-assistant ${message.isStreaming ? "streaming-cursor" : ""}`}
          >
            {message.content ? (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={markdownComponents}
              >
                {message.content}
              </ReactMarkdown>
            ) : message.isStreaming ? (
              <div className="flex items-center gap-1 py-2">
                <span className="typing-dot w-1.5 h-1.5 rounded-full bg-accent" />
                <span className="typing-dot w-1.5 h-1.5 rounded-full bg-accent" />
                <span className="typing-dot w-1.5 h-1.5 rounded-full bg-accent" />
              </div>
            ) : null}
          </div>

          {/* Copy button — appears on hover */}
          {message.content && !message.isStreaming && (
            <div className="mt-2 opacity-0 group-hover/msg:opacity-100 transition-opacity duration-200">
              <button
                onClick={handleCopy}
                className="inline-flex items-center gap-1 text-2xs text-text-muted hover:text-text-secondary transition-colors px-2 py-1 rounded-md hover:bg-bg-elevated"
              >
                {copied ? (
                  <>
                    <IconCheck size={12} className="text-status-success" />
                    <span>Copied</span>
                  </>
                ) : (
                  <>
                    <IconCopy size={12} />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export const MessageItem = memo(MessageItemInner);
