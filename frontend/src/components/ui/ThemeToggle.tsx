/**
 * ThemeToggle — animated sun/moon icon button.
 */

import { motion } from "framer-motion";
import { useStore } from "../../store/useStore";
import { IconSun, IconMoon } from "../ui/icons";

export function ThemeToggle(): React.ReactElement {
  const theme = useStore((s) => s.theme);
  const toggleTheme = useStore((s) => s.toggleTheme);
  const isDark = theme === "dark";

  return (
    <button
      onClick={toggleTheme}
      className="
        relative w-8 h-8 rounded-lg
        flex items-center justify-center
        text-text-muted hover:text-text-primary
        hover:bg-bg-elevated
        transition-all duration-200 focus-ring
      "
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
    >
      <motion.div
        key={theme}
        initial={{ scale: 0.6, opacity: 0, rotate: -30 }}
        animate={{ scale: 1, opacity: 1, rotate: 0 }}
        exit={{ scale: 0.6, opacity: 0, rotate: 30 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
      >
        {isDark ? <IconSun size={16} /> : <IconMoon size={16} />}
      </motion.div>
    </button>
  );
}
