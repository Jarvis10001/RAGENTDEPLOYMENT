/**
 * MessageItem — renders a single user or assistant message.
 *
 * User: right-aligned text, lighter color, no background box.
 * Assistant: left-aligned full-width prose, ReactMarkdown rendered.
 */

import { memo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import { useStore, type Message } from "../../store/useStore";
import { CodeBlock } from "../ui/CodeBlock";

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
  const liveToolCalls = useStore((s) => s.toolCalls);

  const activeToolCalls = message.isStreaming ? liveToolCalls : message.toolCalls;
  const hasToolCalls = activeToolCalls && activeToolCalls.length > 0;

  // Error message
  if (message.isError) {
    return (
      <div className="my-3 p-4 rounded-card border border-status-error/30 bg-status-error/5">
        <p className="text-sm text-status-error/80">{message.content}</p>
        <button
          className="mt-2 text-sm text-accent hover:text-accent-hover transition-colors focus-ring rounded"
          onClick={() => {
            // Retry by dispatching a custom event with the last user message
            window.dispatchEvent(new CustomEvent("ri:retry"));
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  // User message
  if (message.role === "user") {
    return (
      <div className="my-4 flex justify-end">
        <div className="max-w-[80%]">
          <p className="text-sm text-text-secondary text-right leading-relaxed">
            {message.content}
          </p>
        </div>
      </div>
    );
  }

  // Assistant message
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="my-4"
    >
      {/* Detailed Thinking block */}
      {hasToolCalls && (
        <div className="mb-3">
          <button
            onClick={() => setShowThinking((v) => !v)}
            className="flex items-center gap-2 text-2xs text-text-muted hover:text-text-primary transition-colors focus-ring px-2 py-1 rounded-input border border-border bg-bg-surface"
          >
            <span className="font-medium uppercase tracking-wider">
              {showThinking ? "Hide Detailed Thinking" : "Show Detailed Thinking"}
            </span>
            <span className="tabular-nums">({activeToolCalls.length} step{activeToolCalls.length !== 1 ? "s" : ""})</span>
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
                <div className="p-3 bg-bg-elevated rounded-card border border-border text-xs space-y-3">
                  {activeToolCalls.map((tc, idx) => (
                    <div key={idx} className="border-l-2 border-accent/40 pl-3">
                      <div className="font-semibold text-text-primary mb-1">
                        {tc.tool.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                      </div>
                      <div className="text-text-secondary line-clamp-3 font-mono text-[10px] break-all">
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
          <span className="text-text-muted text-sm">Thinking...</span>
        ) : null}
      </div>
    </motion.div>
  );
}

export const MessageItem = memo(MessageItemInner);
