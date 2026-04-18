/**
 * MessageItem — renders a single user or assistant message.
 *
 * User: right-aligned with subtle avatar
 * Assistant: left-aligned with bot avatar, inline chart, copy button
 *
 * The "reasoning" panel shows real agent debug data:
 *  - LLM thinking/chain-of-thought (from Gemini include_thoughts)
 *  - Each tool call with name, input query, output preview, and duration
 *  - Final reasoning trace before the answer is synthesised
 */

import { memo, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import { useStore, type Message, type ToolCall } from "../../store/useStore";
import { CodeBlock } from "../ui/CodeBlock";
import { ChartRenderer } from "../charts/ChartRenderer";
import { IconBot, IconCopy, IconCheck, IconChevronDown, IconRefresh, IconClock } from "../ui/icons";

// ── Helpers ──────────────────────────────────────────────────────

/** Pretty-print a tool name: ecommerce_sql_query → Ecommerce SQL Query */
function formatToolName(raw: string): string {
  return raw
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Truncate long text for display, keeping it readable. */
function truncate(text: string, max: number): string {
  if (!text) return "";
  if (text.length <= max) return text;
  return text.slice(0, max).trimEnd() + " …";
}

/** Map tool name to a display category label. */
function toolBadge(tool: string): { label: string; color: string } {
  if (tool.includes("sql") || tool.includes("analytics"))
    return { label: "SQL", color: "bg-blue-500/15 text-blue-400 border-blue-500/25" };
  if (tool.includes("feedback") || tool.includes("marketing"))
    return { label: "RAG", color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25" };
  if (tool.includes("web") || tool.includes("tavily"))
    return { label: "Web", color: "bg-amber-500/15 text-amber-400 border-amber-500/25" };
  return { label: "Tool", color: "bg-gray-500/15 text-gray-400 border-gray-500/25" };
}

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

// ── Single Tool Call Step ─────────────────────────────────────────

function ToolStep({
  tc,
  index,
  isLast,
}: {
  tc: ToolCall;
  index: number;
  isLast: boolean;
}): React.ReactElement {
  const [expanded, setExpanded] = useState(false);
  const badge = toolBadge(tc.tool);
  const isRunning = tc.status === "running";

  return (
    <div className={`relative pl-6 ${isLast ? "" : "pb-6 border-l-[1.5px] border-accent/40"}`}>
      {/* Timeline dot */}
      <div
        className={`absolute -left-[5px] top-1.5 w-2.5 h-2.5 rounded-full ring-[4px] ring-[#212121] ${
          isRunning ? "bg-amber-400 animate-pulse" : tc.status === "error" ? "bg-red-400" : "bg-accent"
        }`}
      />

      {/* Step header */}
      <div className="flex items-center gap-2 mb-1.5">
        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${badge.color}`}>
          {badge.label}
        </span>
        <span className="text-[12px] font-semibold text-[#E5E7EB]">
          {formatToolName(tc.tool)}
        </span>
        {tc.durationMs > 0 && (
          <span className="text-[10px] text-[#737373] tabular-nums ml-auto">
            {tc.durationMs >= 1000
              ? `${(tc.durationMs / 1000).toFixed(1)}s`
              : `${tc.durationMs}ms`}
          </span>
        )}
        {isRunning && (
          <span className="text-[10px] text-amber-400 animate-pulse ml-auto">running…</span>
        )}
      </div>

      {/* Input query */}
      <div className="mb-1.5">
        <span className="text-[10px] uppercase tracking-wider text-[#737373] font-semibold">Input</span>
        <pre className="mt-0.5 text-[11px] text-[#D1D5DB] bg-black/25 rounded-lg p-2.5 font-mono whitespace-pre-wrap break-all leading-relaxed border border-[#333333]/40 max-h-28 overflow-y-auto reasoning-scrollbar">
          {truncate(tc.input, 600)}
        </pre>
      </div>

      {/* Output (collapsed by default, expandable) */}
      {tc.output && (
        <div>
          <button
            onClick={() => setExpanded((v) => !v)}
            className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-[#737373] font-semibold hover:text-[#9CA3AF] transition-colors"
          >
            <IconChevronDown
              size={10}
              className={`transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
            />
            Output
          </button>
          {expanded && (
            <pre className="mt-0.5 text-[11px] text-[#9CA3AF] bg-black/25 rounded-lg p-2.5 font-mono whitespace-pre-wrap break-all leading-relaxed border border-[#333333]/40 max-h-40 overflow-y-auto reasoning-scrollbar">
              {truncate(tc.output, 1500)}
            </pre>
          )}
        </div>
      )}

      {/* Thinking / Chain-of-thought */}
      {tc.thinking && (
        <div className="mt-2.5 border-t border-[#333333]/60 pt-2">
          <span className="text-[10px] uppercase tracking-wider text-accent/70 font-semibold flex items-center gap-1.5 mb-1">
            <IconBot size={10} className="text-accent" />
            Agent Thinking
          </span>
          <div className="text-[11px] text-[#9CA3AF] italic bg-accent/5 rounded-lg p-2.5 border border-accent/10 max-h-32 overflow-y-auto reasoning-scrollbar leading-relaxed">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
              {truncate(tc.thinking, 2000)}
            </ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────

function MessageItemInner({ message }: MessageItemProps): React.ReactElement {
  const [showThinking, setShowThinking] = useState(false);
  const [copied, setCopied] = useState(false);
  const liveToolCalls = useStore((s) => s.toolCalls);
  const liveChartSpec = useStore((s) => s.currentChartSpec);
  const agentLogs = useStore((s) => s.agentLogs);

  const activeToolCalls = message.isStreaming ? liveToolCalls : message.toolCalls;
  const hasToolCalls = activeToolCalls && activeToolCalls.length > 0;

  // Chart: live spec during streaming, persisted spec for past messages
  const chartSpec = message.isStreaming ? liveChartSpec : message.chartSpec;

  // Agent logs are only live — they don't persist into message history
  const activeLogs = message.isStreaming ? agentLogs : [];

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
                className="flex items-center gap-2 text-2xs text-text-muted hover:text-text-secondary transition-colors focus-ring px-2.5 py-1.5 rounded-lg border border-[#333333] bg-[#212121] hover:bg-[#2A2A2A]"
              >
                <IconChevronDown
                  size={12}
                  className={`transition-transform duration-200 ${showThinking ? "rotate-180" : ""}`}
                />
                <span className="font-medium">
                  {showThinking ? "Hide" : "Show"} reasoning
                </span>
                <span className="tabular-nums text-[#737373]">
                  {activeToolCalls.length} step{activeToolCalls.length !== 1 ? "s" : ""}
                </span>
                {activeToolCalls.some((tc) => tc.durationMs > 0) && (
                  <>
                    <span className="text-[#333333] mx-0.5">•</span>
                    <span className="tabular-nums text-[#737373] flex items-center gap-1">
                      <IconClock size={10} />
                      {(
                        activeToolCalls.reduce((acc, tc) => acc + tc.durationMs, 0) / 1000
                      ).toFixed(1)}s
                    </span>
                  </>
                )}
              </button>

              <AnimatePresence>
                {showThinking && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden mt-3"
                  >
                    <div className="bg-[#212121] rounded-xl border border-[#333333] max-h-96 overflow-y-auto reasoning-scrollbar p-5">
                      {/* Tool call timeline */}
                      {activeToolCalls.map((tc, idx) => (
                        <ToolStep
                          key={idx}
                          tc={tc}
                          index={idx}
                          isLast={idx === activeToolCalls.length - 1 && activeLogs.length === 0}
                        />
                      ))}

                      {/* Final synthesis thinking (from the output chunk) */}
                      {activeLogs.length > 0 && (
                        <div className="relative pl-6 pt-2 border-l-[1.5px] border-transparent">
                          <div className="absolute -left-[5px] top-3 w-2.5 h-2.5 rounded-full bg-purple-400 ring-[4px] ring-[#212121]" />
                          <span className="text-[10px] uppercase tracking-wider text-purple-400/80 font-semibold flex items-center gap-1.5 mb-2">
                            <IconBot size={10} />
                            Final Synthesis Reasoning
                          </span>
                          {activeLogs
                            .filter((log) => !activeToolCalls.some((tc) => tc.thinking === log))
                            .map((log, i) => (
                              <div
                                key={i}
                                className="text-[11px] text-[#9CA3AF] italic bg-purple-500/5 rounded-lg p-2.5 border border-purple-500/10 max-h-32 overflow-y-auto reasoning-scrollbar leading-relaxed mb-2"
                              >
                                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                                  {truncate(log, 2000)}
                                </ReactMarkdown>
                              </div>
                            ))}
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
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

          {/* Inline chart */}
          {chartSpec && !message.isStreaming && (
            <div className="mt-4">
              <ChartRenderer spec={chartSpec} showDataCard={true} />
            </div>
          )}

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
