/**
 * ProgressBar — top-of-page indeterminate loading bar with gradient shimmer.
 * Uses a smoother multi-color gradient and subtle opacity animation.
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
          className="fixed top-0 left-0 right-0 z-50 h-[2px] overflow-hidden"
          style={{ backgroundColor: "rgba(99, 102, 241, 0.08)" }}
        >
          <motion.div
            className="h-full rounded-full"
            style={{
              background:
                "linear-gradient(90deg, transparent, #6366F1, #8B5CF6, #EC4899, #8B5CF6, #6366F1, transparent)",
              width: "40%",
            }}
            animate={{ x: ["-100%", "350%"] }}
            transition={{
              duration: 1.6,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
