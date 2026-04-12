/**
 * ProgressBar — thin indigo loading bar at the very top of the page.
 * Mimics the YouTube/GitHub loading bar pattern.
 */

import { motion, AnimatePresence } from "framer-motion";
import { useStore } from "../../store/useStore";

export function ProgressBar(): React.ReactElement | null {
  const isStreaming = useStore((s) => s.isStreaming);

  return (
    <AnimatePresence>
      {isStreaming && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, transition: { duration: 0.4 } }}
          className="fixed top-0 left-0 right-0 z-50 h-[3px] overflow-hidden"
          style={{ backgroundColor: "rgba(99, 102, 241, 0.15)" }}
        >
          <motion.div
            className="h-full rounded-full"
            style={{
              background:
                "linear-gradient(90deg, transparent, #6366F1, #818CF8, #6366F1, transparent)",
              width: "40%",
            }}
            animate={{ x: ["-100%", "350%"] }}
            transition={{
              duration: 1.8,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
