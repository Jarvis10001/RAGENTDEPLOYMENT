/**
 * RightPanel — tabbed analysis & visualization panel.
 *
 * Tabs: Tools | Data | Sources | Chart
 * - Tools: ToolActivity with timeline
 * - Data: SQL/vector data preview
 * - Sources: Citation links
 * - Chart: Full chart view with expanded rendering
 */

import { AnimatePresence, motion } from "framer-motion";
import { useStore } from "../../store/useStore";
import { ToolActivity } from "../analysis/ToolActivity";
import { DataPreview } from "../analysis/DataPreview";
import { SourceCitations } from "../analysis/SourceCitations";
import { ChartRenderer } from "../charts/ChartRenderer";
import { IconClose, IconBarChart } from "../ui/icons";

const TABS = [
  { key: "tools" as const, label: "Tools" },
  { key: "data" as const, label: "Data" },
  { key: "sources" as const, label: "Sources" },
  { key: "chart" as const, label: "Chart" },
];

export function RightPanel(): React.ReactElement | null {
  const rightPanelOpen = useStore((s) => s.rightPanelOpen);
  const rightPanelTab = useStore((s) => s.rightPanelTab);
  const setRightPanelTab = useStore((s) => s.setRightPanelTab);
  const setRightPanelOpen = useStore((s) => s.setRightPanelOpen);
  const currentChartSpec = useStore((s) => s.currentChartSpec);
  const toolCalls = useStore((s) => s.toolCalls);
  const dataPreview = useStore((s) => s.dataPreview);
  const sourceCitations = useStore((s) => s.sourceCitations);

  if (!rightPanelOpen) return null;

  // Badge counts
  const toolCount = toolCalls.length;
  const hasData = !!dataPreview;
  const sourceCount = sourceCitations.length;
  const hasChart = !!currentChartSpec;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ width: 0, opacity: 0 }}
        animate={{ width: 340, opacity: 1 }}
        exit={{ width: 0, opacity: 0 }}
        transition={{ duration: 0.25, ease: "easeInOut" }}
        className="flex-shrink-0 border-l border-border bg-bg-surface/50 backdrop-blur-sm flex flex-col h-full overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#333333]">
          <h3 className="text-sm font-semibold text-text-primary">Analysis</h3>
          <button
            onClick={() => setRightPanelOpen(false)}
            className="text-text-muted hover:text-text-primary transition-colors p-1 rounded-lg hover:bg-bg-elevated focus-ring"
            aria-label="Close panel"
          >
            <IconClose size={16} />
          </button>
        </div>

        {/* Tab bar */}
        <div className="flex border-b border-[#333333] px-2">
          {TABS.map((tab) => {
            const isActive = rightPanelTab === tab.key;
            const badge =
              tab.key === "tools" ? toolCount :
              tab.key === "sources" ? sourceCount :
              tab.key === "data" && hasData ? 1 :
              tab.key === "chart" && hasChart ? 1 : 0;

            return (
              <button
                key={tab.key}
                onClick={() => setRightPanelTab(tab.key)}
                className={`
                  relative px-3 py-2.5 text-xs font-medium
                  transition-colors duration-200
                  ${
                    isActive
                      ? "text-accent"
                      : "text-[#9CA3AF] hover:text-[#D1D5DB]"
                  }
                `}
              >
                <span className="flex items-center gap-1">
                  {tab.label}
                  {badge > 0 && (
                    <span className={`
                      inline-flex items-center justify-center
                      min-w-[16px] h-4 px-1 rounded-full text-[10px] font-semibold
                      ${isActive ? "bg-accent/15 text-accent" : "bg-bg-elevated text-text-muted"}
                    `}>
                      {badge}
                    </span>
                  )}
                </span>
                {isActive && (
                  <motion.div
                    layoutId="tab-indicator"
                    className="absolute bottom-0 left-2 right-2 h-[2px] bg-accent rounded-full"
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                  />
                )}
              </button>
            );
          })}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          <AnimatePresence mode="wait">
            {rightPanelTab === "tools" && (
              <motion.div
                key="tools"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
              >
                <ToolActivity />
              </motion.div>
            )}

            {rightPanelTab === "data" && (
              <motion.div
                key="data"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
              >
                <DataPreview />
              </motion.div>
            )}

            {rightPanelTab === "sources" && (
              <motion.div
                key="sources"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
              >
                <SourceCitations />
              </motion.div>
            )}

            {rightPanelTab === "chart" && (
              <motion.div
                key="chart"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className="p-3"
              >
                {currentChartSpec ? (
                  <ChartRenderer spec={currentChartSpec} height={380} />
                ) : (
                  <div className="flex flex-col items-center justify-center h-60 text-center">
                    <div className="w-12 h-12 rounded-xl bg-bg-elevated flex items-center justify-center mb-3">
                      <IconBarChart size={20} className="text-text-muted" />
                    </div>
                    <p className="text-sm text-text-muted">
                      No chart available
                    </p>
                    <p className="text-xs text-text-muted/60 mt-1.5 max-w-[220px]">
                      Charts are generated automatically when query results contain tabular data
                    </p>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
