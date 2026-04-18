/**
 * Axios instance and API helpers for the Revenue Intelligence backend.
 */

import axios from "axios";
import type { ChartSpec, ChatMode } from "../store/useStore";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 120_000,
  headers: { "Content-Type": "application/json" },
});

// ── Types for SSE events ─────────────────────────────────────────

export interface TokenEvent {
  type: "token";
  content: string;
}

export interface ToolStartEvent {
  type: "tool_start";
  tool: string;
  input: string;
  thinking?: string;
}

export interface ToolEndEvent {
  type: "tool_end";
  tool: string;
  output: string;
  duration_ms: number;
}

export interface DoneEvent {
  type: "done";
  full_response: string;
}

export interface ErrorEvent {
  type: "error";
  message: string;
}

export interface ChartEvent {
  type: "chart";
  spec: ChartSpec;
}

export interface AgentLogEvent {
  type: "agent_log";
  log_type: string;
  content: string;
}

export type SSEEvent =
  | TokenEvent
  | ToolStartEvent
  | ToolEndEvent
  | DoneEvent
  | ErrorEvent
  | ChartEvent
  | AgentLogEvent;

// ── History item for API ─────────────────────────────────────────

export interface HistoryItem {
  role: "user" | "assistant";
  content: string;
}

// ── SSE streaming via fetch ──────────────────────────────────────

export interface StreamChatParams {
  message: string;
  sessionId: string;
  history: HistoryItem[];
  mode?: ChatMode;
  onEvent: (event: SSEEvent) => void;
  onError: (error: string) => void;
  onDone: () => void;
  signal?: AbortSignal;
}

export async function streamChat({
  message,
  sessionId,
  history,
  mode = "fast",
  onEvent,
  onError,
  onDone,
  signal,
}: StreamChatParams): Promise<void> {
  const url = `${API_URL}/api/chat`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        history,
        mode,
      }),
      signal,
    });

    if (!response.ok) {
      onError(`Server error: ${response.status} ${response.statusText}`);
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
      onError("No response body");
      return;
    }

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      // Keep the last incomplete line in the buffer
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith("data: ")) continue;

        const jsonStr = trimmed.slice(6);
        try {
          const event = JSON.parse(jsonStr) as SSEEvent;
          onEvent(event);
        } catch {
          // skip malformed lines
        }
      }
    }

    // Process any remaining data in buffer
    if (buffer.trim().startsWith("data: ")) {
      const jsonStr = buffer.trim().slice(6);
      try {
        const event = JSON.parse(jsonStr) as SSEEvent;
        onEvent(event);
      } catch {
        // skip
      }
    }

    onDone();
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === "AbortError") {
      return;
    }
    const message =
      err instanceof Error ? err.message : "Connection failed";
    onError(message);
  }
}

// ── REST helpers ─────────────────────────────────────────────────

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await apiClient.get<{ status: string }>("/api/health");
    return res.data.status === "ok";
  } catch {
    return false;
  }
}

export async function clearSession(sessionId: string): Promise<boolean> {
  try {
    const res = await apiClient.delete<{ cleared: boolean }>(
      `/api/session/${sessionId}`
    );
    return res.data.cleared;
  } catch {
    return false;
  }
}
