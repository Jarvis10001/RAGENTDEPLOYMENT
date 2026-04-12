/**
 * Keyboard shortcuts hook.
 *
 * ⌘K / Ctrl+K → focus input
 * ⌘N / Ctrl+N → new conversation
 * Escape → collapse right panel
 */

import { useEffect } from "react";
import { useStore } from "../store/useStore";

export function useKeyboard(): void {
  const setRightPanelOpen = useStore((s) => s.setRightPanelOpen);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const meta = e.metaKey || e.ctrlKey;

      // ⌘K or Ctrl+K → focus input
      if (meta && e.key === "k") {
        e.preventDefault();
        const input = document.getElementById("chat-input");
        if (input) {
          input.focus();
        }
      }

      // ⌘N or Ctrl+N → new conversation
      if (meta && e.key === "n") {
        e.preventDefault();
        // Dispatch a custom event that Sidebar listens for
        window.dispatchEvent(new CustomEvent("ri:new-conversation"));
      }

      // Escape → collapse right panel
      if (e.key === "Escape") {
        setRightPanelOpen(false);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [setRightPanelOpen]);
}
