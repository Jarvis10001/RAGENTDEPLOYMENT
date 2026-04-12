/**
 * RightPanel — 320px toggleable analysis panel.
 *
 * Three sections: Tool Activity, Data Preview, Source Citations.
 */

import { motion, AnimatePresence } from "framer-motion";
import { useStore } from "../../store/useStore";
import { ToolActivity } from "../analysis/ToolActivity";
import { DataPreview } from "../analysis/DataPreview";
import { SourceCitations } from "../analysis/SourceCitations";

function PanelSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}): React.ReactElement {
  return (
    <div className="mb-4">
      <h3 className="text-2xs font-semibold text-text-muted uppercase tracking-wider mb-3">
        {title}
      </h3>
      {children}
    </div>
  );
}

export function RightPanel(): React.ReactElement | null {
  const rightPanelOpen = useStore((s) => s.rightPanelOpen);

  return (
    <AnimatePresence>
      {rightPanelOpen && (
        <motion.div
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 320, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.25, ease: "easeInOut" }}
          className="
            flex-shrink-0 border-l border-border bg-bg-surface
            h-full overflow-hidden
          "
        >
          <div className="w-right-panel h-full overflow-y-auto p-4">
            {/* Header */}
            <h2 className="text-[13px] font-semibold text-text-muted uppercase tracking-wider mb-5">
              Analysis Details
            </h2>

            <PanelSection title="Tool Activity">
              <ToolActivity />
            </PanelSection>

            <div className="border-t border-border-muted my-4" />

            <PanelSection title="Data Preview">
              <DataPreview />
            </PanelSection>

            <div className="border-t border-border-muted my-4" />

            <PanelSection title="Source Citations">
              <SourceCitations />
            </PanelSection>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
