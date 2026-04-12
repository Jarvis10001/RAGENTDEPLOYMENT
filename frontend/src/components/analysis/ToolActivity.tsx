/**
 * ToolActivity — shows which tools were called for the last response.
 * Each tool as a row: name + execution time + status dot.
 * Expandable to show the exact SQL query or vector search phrase.
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useStore, type ToolCall } from "../../store/useStore";

function StatusDot({ status }: { status: ToolCall["status"] }): React.ReactElement {
  const color =
    status === "success"
      ? "bg-status-success"
      : status === "error"
        ? "bg-status-error"
        : "bg-status-warning";

  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${color} ${
        status === "running" ? "animate-pulse" : ""
      }`}
    />
  );
}

function formatToolName(name: string): string {
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function ToolRow({ tool }: { tool: ToolCall }): React.ReactElement {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border-b border-border-muted last:border-b-0">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="
          w-full flex items-center justify-between gap-2 py-2.5 px-1
          text-left text-sm hover:bg-bg-elevated/50 transition-colors
          rounded-input focus-ring
        "
      >
        <span className="text-text-primary font-medium truncate flex-1">
          {formatToolName(tool.tool)}
        </span>
        <span className="text-2xs text-text-muted tabular-nums whitespace-nowrap">
          {tool.durationMs > 0 ? `${tool.durationMs}ms` : "..."}
        </span>
        <StatusDot status={tool.status} />
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-1 pb-3">
              {tool.input && (
                <div className="mb-2">
                  <span className="text-2xs text-text-muted uppercase tracking-wider">
                    Input
                  </span>
                  <pre className="mt-1 p-2 text-xs font-mono bg-bg-elevated rounded-input border border-border-muted text-text-secondary overflow-x-auto max-h-32 overflow-y-auto">
                    {tool.input}
                  </pre>
                </div>
              )}
              {tool.output && (
                <div>
                  <span className="text-2xs text-text-muted uppercase tracking-wider">
                    Output
                  </span>
                  <pre className="mt-1 p-2 text-xs font-mono bg-bg-elevated rounded-input border border-border-muted text-text-secondary overflow-x-auto max-h-48 overflow-y-auto">
                    {tool.output.slice(0, 1500)}
                    {tool.output.length > 1500 ? "\n..." : ""}
                  </pre>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function ToolActivity(): React.ReactElement {
  const toolCalls = useStore((s) => s.toolCalls);

  if (toolCalls.length === 0) {
    return (
      <div className="py-4 text-center text-sm text-text-muted">
        No tool activity yet
      </div>
    );
  }

  return (
    <div>
      {toolCalls.map((tool, idx) => (
        <ToolRow key={`${tool.tool}-${idx}`} tool={tool} />
      ))}
    </div>
  );
}
