/**
 * TopBar — slim top navigation bar with breadcrumb title,
 * source pills with icons, and panel toggle.
 */

import { motion, AnimatePresence } from "framer-motion";
import { useStore } from "../../store/useStore";
import { IconMenu, IconPanelRight, IconDatabase, IconLayers, IconGlobe, IconBarChart } from "../ui/icons";

const TOOL_META: Record<string, { label: string; Icon: React.ComponentType<{ size?: number; className?: string }> }> = {
  ecommerce_sql_query: { label: "SQL", Icon: IconDatabase },
  ecommerce_analytics_query: { label: "Analytics", Icon: IconBarChart },
  omnichannel_feedback_search: { label: "Feedback", Icon: IconLayers },
  marketing_content_search: { label: "Marketing", Icon: IconLayers },
  web_market_search: { label: "Web", Icon: IconGlobe },
};

export function TopBar(): React.ReactElement {
  const sidebarOpen = useStore((s) => s.sidebarOpen);
  const rightPanelOpen = useStore((s) => s.rightPanelOpen);
  const lastToolsUsed = useStore((s) => s.lastToolsUsed);
  const isStreaming = useStore((s) => s.isStreaming);
  const toggleSidebar = useStore((s) => s.toggleSidebar);
  const toggleRightPanel = useStore((s) => s.toggleRightPanel);
  const getActiveConversation = useStore((s) => s.getActiveConversation);

  const activeConv = getActiveConversation();

  return (
    <div className="h-topbar flex-shrink-0 border-b border-border flex items-center justify-between px-4 bg-bg-surface/40 backdrop-blur-sm">
      {/* Left cluster */}
      <div className="flex items-center gap-3 min-w-0">
        {!sidebarOpen && (
          <button
            onClick={toggleSidebar}
            className="text-text-muted hover:text-text-primary transition-colors focus-ring rounded-lg p-1 hover:bg-bg-elevated"
            aria-label="Open sidebar"
          >
            <IconMenu size={18} />
          </button>
        )}

        {/* Title */}
        <div className="flex items-center gap-2 min-w-0">

          <h2 className="text-sm font-semibold text-text-primary truncate">
            {activeConv?.title || "E-Commerce Intelligence"}
          </h2>
        </div>
      </div>

      {/* Right cluster */}
      <div className="flex items-center gap-2">
        {/* Source pills */}
        <AnimatePresence>
          {lastToolsUsed.map((t) => {
            const meta = TOOL_META[t] || { label: t, Icon: IconDatabase };
            const { label, Icon } = meta;
            return (
              <motion.span
                key={t}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="
                  inline-flex items-center gap-1.5 px-2.5 py-1
                  rounded-full text-2xs font-medium
                  bg-bg-elevated border border-border/50
                  text-text-secondary select-none
                "
              >
                <Icon size={11} />
                {label}
              </motion.span>
            );
          })}
        </AnimatePresence>

        {/* Panel toggle */}
        <button
          onClick={toggleRightPanel}
          className={`
            text-text-muted hover:text-text-primary
            p-1.5 rounded-lg transition-all focus-ring
            ${rightPanelOpen ? "bg-accent/10 text-accent" : "hover:bg-bg-elevated"}
          `}
          aria-label={rightPanelOpen ? "Close analysis panel" : "Open analysis panel"}
        >
          <IconPanelRight size={18} />
        </button>
      </div>
    </div>
  );
}
