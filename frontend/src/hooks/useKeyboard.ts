/**
 * Keyboard shortcuts hook.
 *
 * ⌘K / Ctrl+K → toggle command palette
 * ⌘N / Ctrl+N → new conversation
 * Escape → close palette → then collapse right panel
 */

import { useEffect } from "react";
import { useStore } from "../store/useStore";

export function useKeyboard(): void {
  const setRightPanelOpen = useStore((s) => s.setRightPanelOpen);
  const commandPaletteOpen = useStore((s) => s.commandPaletteOpen);
  const toggleCommandPalette = useStore((s) => s.toggleCommandPalette);
  const setCommandPaletteOpen = useStore((s) => s.setCommandPaletteOpen);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const meta = e.metaKey || e.ctrlKey;

      // ⌘K or Ctrl+K → toggle command palette
      if (meta && e.key === "k") {
        e.preventDefault();
        toggleCommandPalette();
      }

      // ⌘N or Ctrl+N → new conversation
      if (meta && e.key === "n") {
        e.preventDefault();
        // Close palette if open
        setCommandPaletteOpen(false);
        // Dispatch a custom event that Sidebar listens for
        window.dispatchEvent(new CustomEvent("ri:new-conversation"));
      }

      // Escape → close palette first, then right panel
      if (e.key === "Escape") {
        if (useStore.getState().commandPaletteOpen) {
          setCommandPaletteOpen(false);
        } else {
          setRightPanelOpen(false);
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [setRightPanelOpen, commandPaletteOpen, toggleCommandPalette, setCommandPaletteOpen]);
}
