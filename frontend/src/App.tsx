/**
 * App — root component with three-panel layout.
 *
 * Left: Sidebar (240px, collapsible)
 * Center: TopBar + MessageList + InputBar
 * Right: RightPanel (320px, toggleable)
 */

import { useCallback } from "react";
import { useStore } from "./store/useStore";
import { useStream } from "./hooks/useStream";
import { useKeyboard } from "./hooks/useKeyboard";
import { ProgressBar } from "./components/ui/ProgressBar";
import { Sidebar } from "./components/layout/Sidebar";
import { TopBar } from "./components/layout/TopBar";
import { RightPanel } from "./components/layout/RightPanel";
import { MessageList } from "./components/chat/MessageList";
import { InputBar } from "./components/chat/InputBar";

export default function App(): React.ReactElement {
  const connectionError = useStore((s) => s.connectionError);
  const { sendMessage, isStreaming } = useStream();

  // Register keyboard shortcuts
  useKeyboard();

  const handleSelectQuestion = useCallback(
    (question: string) => {
      sendMessage(question);
    },
    [sendMessage]
  );

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-bg-primary">
      {/* Progress bar at very top */}
      <ProgressBar />

      {/* Connection error bar */}
      {connectionError && (
        <div className="flex-shrink-0 bg-status-error/90 text-white text-xs text-center py-1.5 px-4">
          {connectionError}
          <button
            onClick={() => useStore.getState().setConnectionError(null)}
            className="ml-3 underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left sidebar */}
        <Sidebar />

        {/* Main content area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <TopBar />
          <MessageList onSelectQuestion={handleSelectQuestion} />
          <InputBar onSend={sendMessage} isStreaming={isStreaming} />
        </div>

        {/* Right panel */}
        <RightPanel />
      </div>
    </div>
  );
}
