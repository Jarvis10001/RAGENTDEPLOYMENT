import { motion, AnimatePresence } from "framer-motion";
import { createPortal } from "react-dom";
import { useEffect, useState } from "react";

export function ConfirmModal({
  isOpen,
  title,
  message,
  onConfirm,
  onCancel,
}: {
  isOpen: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Prevent body scrolling when modal is open
  if (typeof window !== "undefined") {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
  }

  const modalContent = (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[9999] flex items-center justify-center p-4"
          onClick={onCancel}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0, y: 10 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0, y: 10 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            onClick={(e) => e.stopPropagation()}
            className="bg-bg-surface border border-border w-full max-w-sm rounded-[12px] shadow-2xl overflow-hidden"
          >
            <div className="p-5">
              <h3 className="text-base font-semibold text-text-primary mb-2">
                {title}
              </h3>
              <p className="text-sm text-text-secondary leading-relaxed">
                {message}
              </p>
            </div>
            <div className="bg-bg-elevated px-5 py-4 border-t border-border flex justify-end gap-3">
              <button
                onClick={onCancel}
                className="px-4 py-1.5 rounded-input text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-bg-primary transition-colors focus-[shadow.var(--focus-ring)] outline-none"
              >
                Cancel
              </button>
              <button
                onClick={onConfirm}
                className="px-4 py-1.5 rounded-input text-sm font-medium bg-status-error/10 text-status-error hover:bg-status-error/20 transition-colors focus-[shadow.var(--focus-ring)] outline-none"
              >
                Delete
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );

  if (!mounted) return null;

  return createPortal(modalContent, document.body);
}
