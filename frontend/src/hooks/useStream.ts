/**
 * SSE streaming hook — connects to POST /api/chat and dispatches
 * events to the Zustand store in real time.
 */

import { useCallback, useRef, useEffect } from "react";
import { streamChat, type SSEEvent, type HistoryItem } from "../lib/api";
import {
  useStore,
  createMessage,
  createConversation,
} from "../store/useStore";

interface UseStreamReturn {
  sendMessage: (message: string) => void;
  cancelStream: () => void;
  isStreaming: boolean;
}

// Tool name → display category mapping
function toolCategory(tool: string): string {
  if (tool.includes("sql") || tool.includes("analytics")) return "SQL";
  if (tool.includes("feedback") || tool.includes("marketing")) return "Vector";
  if (tool.includes("web") || tool.includes("tavily")) return "Web";
  return "Tool";
}

// Try to extract URLs from web search output for citations
function extractUrls(text: string): Array<{ url: string; title: string }> {
  const urlRegex = /https?:\/\/[^\s"'<>)]+/g;
  const matches = text.match(urlRegex) || [];
  return matches.slice(0, 10).map((url) => ({
    url,
    title: new URL(url).hostname.replace("www.", ""),
  }));
}

export function useStream(): UseStreamReturn {
  const abortRef = useRef<AbortController | null>(null);
  const fullContentRef = useRef("");

  const isStreaming = useStore((s) => s.isStreaming);
  const activeConversationId = useStore((s) => s.activeConversationId);
  const conversations = useStore((s) => s.conversations);

  const setStreaming = useStore((s) => s.setStreaming);
  const addConversation = useStore((s) => s.addConversation);
  const addMessage = useStore((s) => s.addMessage);
  const updateLastAssistantMessage = useStore(
    (s) => s.updateLastAssistantMessage
  );
  const finalizeAssistantMessage = useStore((s) => s.finalizeAssistantMessage);
  const addToolCall = useStore((s) => s.addToolCall);
  const updateToolCall = useStore((s) => s.updateToolCall);
  const clearAnalysis = useStore((s) => s.clearAnalysis);
  const setDataPreview = useStore((s) => s.setDataPreview);
  const addCitation = useStore((s) => s.addCitation);
  const setLastToolsUsed = useStore((s) => s.setLastToolsUsed);
  const setConnectionError = useStore((s) => s.setConnectionError);
  const setRightPanelOpen = useStore((s) => s.setRightPanelOpen);
  const setChartSpec = useStore((s) => s.setChartSpec);
  const chatMode = useStore((s) => s.chatMode);

  const sendMessage = useCallback(
    (message: string) => {
      if (isStreaming) return;

      // Cancel any previous stream
      abortRef.current?.abort();

      const controller = new AbortController();
      abortRef.current = controller;

      // Determine conversation — create if none active
      let convId = activeConversationId;
      const autoTitle = message.length > 40 ? message.slice(0, 40) + "…" : message;

      if (!convId) {
        const conv = createConversation(autoTitle);
        addConversation(conv);
        convId = conv.id;
      } else {
        const conv = conversations.find((c) => c.id === convId);
        if (conv && conv.messages.length === 0 && conv.title === "New conversation") {
          useStore.getState().updateConversationTitle(convId, autoTitle);
        }
      }

      const currentConvId = convId;

      // Clear previous analysis
      clearAnalysis();

      // Add user message
      const userMsg = createMessage("user", message);
      addMessage(currentConvId, userMsg);

      // Add placeholder assistant message
      const assistantMsg = createMessage("assistant", "", {
        isStreaming: true,
      });
      addMessage(currentConvId, assistantMsg);

      // Start streaming
      setStreaming(true);
      setConnectionError(null);
      fullContentRef.current = "";

      // Build history from current conversation
      const conv = conversations.find((c) => c.id === currentConvId);
      const history: HistoryItem[] = (conv?.messages || [])
        .slice(-12)
        .map((m) => ({ role: m.role, content: m.content }));

      const toolsUsed = new Set<string>();

      const handleEvent = (event: SSEEvent) => {
        switch (event.type) {
          case "token": {
            fullContentRef.current += event.content;
            updateLastAssistantMessage(currentConvId, fullContentRef.current);
            break;
          }

          case "tool_start": {
            addToolCall({
              tool: event.tool,
              input: event.input,
              output: "",
              durationMs: 0,
              status: "running",
            });
            toolsUsed.add(toolCategory(event.tool));
            setRightPanelOpen(true);
            break;
          }

          case "tool_end": {
            updateToolCall(event.tool, {
              output: event.output,
              durationMs: event.duration_ms,
              status: "success",
            });

            // Extract data preview from SQL tools
            if (
              event.tool.includes("sql") ||
              event.tool.includes("analytics")
            ) {
              setDataPreview({ type: "sql", data: event.output });
            }

            // Extract data preview from vector/RAG tools
            if (
              event.tool.includes("feedback") ||
              event.tool.includes("marketing")
            ) {
              setDataPreview({ type: "vector", data: event.output });
            }

            // Extract citations from web search
            if (event.tool.includes("web") || event.tool.includes("tavily")) {
              const urls = extractUrls(event.output);
              urls.forEach((c) => addCitation(c));
            }
            break;
          }

          case "chart": {
            setChartSpec(event.spec);
            break;
          }

          case "done": {
            finalizeAssistantMessage(currentConvId, event.full_response);
            setStreaming(false);
            setLastToolsUsed(Array.from(toolsUsed));
            break;
          }

          case "error": {
            // Add error as assistant message
            finalizeAssistantMessage(
              currentConvId,
              fullContentRef.current || ""
            );
            const errorMsg = createMessage("assistant", event.message, {
              isError: true,
            });
            addMessage(currentConvId, errorMsg);
            setStreaming(false);
            break;
          }
        }
      };

      const handleError = (error: string) => {
        setConnectionError(error);
        finalizeAssistantMessage(
          currentConvId,
          fullContentRef.current || ""
        );
        if (!fullContentRef.current) {
          // Remove the empty streaming message and add error
          const errorMsg = createMessage("assistant", error, {
            isError: true,
          });
          addMessage(currentConvId, errorMsg);
        }
        setStreaming(false);
      };

      const handleDone = () => {
        if (useStore.getState().isStreaming) {
          setStreaming(false);
          if (fullContentRef.current) {
            finalizeAssistantMessage(currentConvId, fullContentRef.current);
          }
        }
      };

      streamChat({
        message,
        sessionId: currentConvId,
        history,
        mode: chatMode,
        onEvent: handleEvent,
        onError: handleError,
        onDone: handleDone,
        signal: controller.signal,
      });
    },
    [
      isStreaming,
      activeConversationId,
      conversations,
      addConversation,
      addMessage,
      updateLastAssistantMessage,
      finalizeAssistantMessage,
      clearAnalysis,
      addToolCall,
      updateToolCall,
      setDataPreview,
      addCitation,
      setStreaming,
      setConnectionError,
      setLastToolsUsed,
      setRightPanelOpen,
      setChartSpec,
      chatMode,
    ]
  );

  const cancelStream = useCallback(() => {
    abortRef.current?.abort();
    setStreaming(false);
    
    // Finalize the message so the UI stops showing the streaming cursor/thinking
    const currentState = useStore.getState();
    const activeId = currentState.activeConversationId;
    if (activeId) {
      currentState.finalizeAssistantMessage(activeId, fullContentRef.current);
    }
  }, [setStreaming]);

  useEffect(() => {
    const handleCancel = () => cancelStream();
    window.addEventListener("ri:cancel-stream", handleCancel);
    return () => window.removeEventListener("ri:cancel-stream", handleCancel);
  }, [cancelStream]);

  return { sendMessage, cancelStream, isStreaming };
}
