/**
 * ToolActivity — displays tool calls with icons, status badges,
 * and a vertical timeline connector.
 */

import { useStore } from "../../store/useStore";
import { IconDatabase, IconBarChart, IconLayers, IconGlobe, IconZap } from "../ui/icons";

const TOOL_ICON_MAP: Record<string, React.ComponentType<{ size?: number; className?: string }>> = {
  ecommerce_sql_query: IconDatabase,
  ecommerce_analytics_query: IconBarChart,
  omnichannel_feedback_search: IconLayers,
  marketing_content_search: IconLayers,
  web_market_search: IconGlobe,
};

function formatToolName(name: string): string {
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function StatusBadge({ status }: { status: string }): React.ReactElement {
  const styles = {
    running: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    success: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    error: "bg-red-500/10 text-red-400 border-red-500/20",
  };
  const labels = { running: "Running", success: "Done", error: "Error" };
  const s = status as keyof typeof styles;
  return (
    <span
      className={`
        text-[10px] font-semibold px-2 py-0.5 rounded-full border
        ${styles[s] || styles.running}
      `}
    >
      {labels[s] || status}
    </span>
  );
}

export function ToolActivity(): React.ReactElement {
  const toolCalls = useStore((s) => s.toolCalls);

  if (toolCalls.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-60 text-center px-4">
        <div className="w-12 h-12 rounded-xl bg-bg-elevated flex items-center justify-center mb-3">
          <IconZap size={20} className="text-text-muted" />
        </div>
        <p className="text-sm text-text-muted">No tool activity yet</p>
        <p className="text-xs text-text-muted/60 mt-1.5 max-w-[220px]">
          Tool calls will appear here as the agent processes your query
        </p>
      </div>
    );
  }

  return (
    <div className="p-3">
      <div className="space-y-0">
        {toolCalls.map((tc, idx) => {
          const Icon = TOOL_ICON_MAP[tc.tool] || IconZap;
          const isLast = idx === toolCalls.length - 1;

          return (
            <div key={idx} className="flex gap-3">
              {/* Timeline */}
              <div className="flex flex-col items-center flex-shrink-0">
                <div
                  className={`
                    w-7 h-7 rounded-lg flex items-center justify-center
                    ${tc.status === "running" ? "bg-accent/15 text-accent animate-pulse" : ""}
                    ${tc.status === "success" ? "bg-emerald-500/10 text-emerald-400" : ""}
                    ${tc.status === "error" ? "bg-red-500/10 text-red-400" : ""}
                  `}
                >
                  <Icon size={14} />
                </div>
                {!isLast && (
                  <div className="w-px flex-1 bg-border/40 min-h-[16px] my-1" />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 pb-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-text-primary">
                    {formatToolName(tc.tool)}
                  </span>
                  <div className="flex items-center gap-2">
                    {tc.durationMs > 0 && (
                      <span className="text-[10px] text-text-muted tabular-nums">
                        {(tc.durationMs / 1000).toFixed(1)}s
                      </span>
                    )}
                    <StatusBadge status={tc.status} />
                  </div>
                </div>

                {/* Input */}
                <div className="text-[11px] text-text-muted line-clamp-2 font-mono mb-1 break-all leading-relaxed">
                  {tc.input}
                </div>

                {/* Output preview */}
                {tc.output && tc.status !== "running" && (
                  <details className="text-[11px] text-text-secondary">
                    <summary className="cursor-pointer hover:text-text-primary transition-colors select-none py-0.5">
                      View output
                    </summary>
                    <pre className="mt-1 p-2 bg-bg-elevated/60 rounded-lg overflow-x-auto text-[10px] font-mono leading-relaxed max-h-40 overflow-y-auto whitespace-pre-wrap">
                      {tc.output.substring(0, 500)}
                      {tc.output.length > 500 ? "…" : ""}
                    </pre>
                  </details>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
