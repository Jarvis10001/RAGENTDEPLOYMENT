/**
 * ThemeToggle — Dark/Light pill switch. No icons, text labels only.
 */

import { useStore } from "../../store/useStore";

export function ThemeToggle(): React.ReactElement {
  const theme = useStore((s) => s.theme);
  const toggleTheme = useStore((s) => s.toggleTheme);

  return (
    <button
      onClick={toggleTheme}
      className="
        relative flex h-8 w-full items-center rounded-pill
        border border-border bg-bg-surface
        text-xs font-medium text-text-secondary
        transition-colors hover:border-accent/30
        focus-ring
      "
      id="theme-toggle"
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
    >
      <span
        className={`
          flex-1 text-center py-1 z-10 transition-colors duration-200
          ${theme === "dark" ? "text-text-primary" : "text-text-muted"}
        `}
      >
        Dark
      </span>
      <span
        className={`
          flex-1 text-center py-1 z-10 transition-colors duration-200
          ${theme === "light" ? "text-text-primary" : "text-text-muted"}
        `}
      >
        Light
      </span>
      {/* Sliding indicator */}
      <span
        className={`
          absolute top-[3px] h-[calc(100%-6px)] w-[calc(50%-4px)] rounded-pill
          bg-bg-elevated border border-border-muted
          transition-all duration-300 ease-out
          ${theme === "dark" ? "left-[3px]" : "left-[calc(50%+1px)]"}
        `}
      />
    </button>
  );
}
