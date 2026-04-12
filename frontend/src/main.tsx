/**
 * Application entry point.
 *
 * Mounts the React app, applies saved theme, and renders <App />.
 */

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { applyTheme } from "./lib/storage";
import { useStore } from "./store/useStore";
import "./styles/globals.css";

// Apply saved theme before first render to avoid flash
applyTheme(useStore.getState().theme);

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element not found");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>
);
