/**
 * Zustand global state for E-commerce Intelligence Agent.
 *
 * Single source of truth for conversations, streaming state,
 * tool activity, and UI panels.
 */

import { create } from "zustand";
import {
  loadConversations,
  saveConversations,
  loadTheme,
  saveTheme,
  applyTheme,
  type ThemeValue,
} from "../lib/storage";

// ── Domain types ─────────────────────────────────────────────────

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  isStreaming?: boolean;
  isError?: boolean;
  toolCalls?: ToolCall[];
  dataPreview?: DataPreview | null;
  sourceCitations?: Citation[];
  lastToolsUsed?: string[];
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
}

export interface ToolCall {
  tool: string;
  input: string;
  output: string;
  durationMs: number;
  status: "running" | "success" | "error";
}

export interface DataPreview {
  type: "sql" | "vector";
  data: string;
}

export interface Citation {
  url: string;
  title: string;
}

// ── Store shape ──────────────────────────────────────────────────

interface AppState {
  // Conversations
  conversations: Conversation[];
  activeConversationId: string | null;

  // UI panels
  sidebarOpen: boolean;
  rightPanelOpen: boolean;
  theme: ThemeValue;

  // Streaming
  isStreaming: boolean;
  streamingContent: string;

  // Analysis panel data
  toolCalls: ToolCall[];
  dataPreview: DataPreview | null;
  sourceCitations: Citation[];
  lastToolsUsed: string[];

  // Error
  connectionError: string | null;

  // Actions — Conversations
  setConversations: (conversations: Conversation[]) => void;
  setActiveConversation: (id: string | null) => void;
  addConversation: (conversation: Conversation) => void;
  deleteConversation: (id: string) => void;
  updateConversationTitle: (id: string, title: string) => void;
  addMessage: (conversationId: string, message: Message) => void;
  updateLastAssistantMessage: (conversationId: string, content: string) => void;
  finalizeAssistantMessage: (conversationId: string, content: string) => void;

  // Actions — UI
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleRightPanel: () => void;
  setRightPanelOpen: (open: boolean) => void;
  toggleTheme: () => void;

  // Actions — Streaming
  setStreaming: (streaming: boolean) => void;
  setStreamingContent: (content: string) => void;
  appendStreamingContent: (token: string) => void;

  // Actions — Analysis
  addToolCall: (toolCall: ToolCall) => void;
  updateToolCall: (tool: string, update: Partial<ToolCall>) => void;
  clearAnalysis: () => void;
  setDataPreview: (preview: DataPreview | null) => void;
  addCitation: (citation: Citation) => void;
  setLastToolsUsed: (tools: string[]) => void;

  // Actions — Error
  setConnectionError: (error: string | null) => void;

  // Computed helpers
  getActiveConversation: () => Conversation | undefined;
}

// ── Helpers ──────────────────────────────────────────────────────

function generateId(): string {
  return crypto.randomUUID();
}

export function createMessage(
  role: "user" | "assistant",
  content: string,
  options?: { isStreaming?: boolean; isError?: boolean }
): Message {
  return {
    id: generateId(),
    role,
    content,
    timestamp: Date.now(),
    isStreaming: options?.isStreaming,
    isError: options?.isError,
  };
}

export function createConversation(title: string): Conversation {
  return {
    id: generateId(),
    title,
    messages: [],
    createdAt: Date.now(),
    updatedAt: Date.now(),
  };
}

// ── Store ────────────────────────────────────────────────────────

export const useStore = create<AppState>((set, get) => ({
  // Initial state
  conversations: loadConversations(),
  activeConversationId: null,
  sidebarOpen: true,
  rightPanelOpen: false,
  theme: loadTheme(),
  isStreaming: false,
  streamingContent: "",
  toolCalls: [],
  dataPreview: null,
  sourceCitations: [],
  lastToolsUsed: [],
  connectionError: null,

  // ── Conversations ────────────────────────────────────────────

  setConversations: (conversations) => {
    set({ conversations });
    saveConversations(conversations);
  },

  setActiveConversation: (id) => {
    const conv = get().conversations.find((c) => c.id === id);
    const lastAsst = conv?.messages
      .slice()
      .reverse()
      .find((m) => m.role === "assistant" && !m.isStreaming);

    set({
      activeConversationId: id,
      toolCalls: lastAsst?.toolCalls || [],
      dataPreview: lastAsst?.dataPreview || null,
      sourceCitations: lastAsst?.sourceCitations || [],
      lastToolsUsed: lastAsst?.lastToolsUsed || [],
    });
  },

  addConversation: (conversation) => {
    const conversations = [conversation, ...get().conversations];
    set({ conversations, activeConversationId: conversation.id });
    saveConversations(conversations);
  },

  deleteConversation: (id) => {
    const conversations = get().conversations.filter((c) => c.id !== id);
    const activeId = get().activeConversationId;
    set({
      conversations,
      activeConversationId: activeId === id ? null : activeId,
    });
    saveConversations(conversations);
  },

  updateConversationTitle: (id, title) => {
    const conversations = get().conversations.map((c) =>
      c.id === id ? { ...c, title, updatedAt: Date.now() } : c
    );
    set({ conversations });
    saveConversations(conversations);
  },

  addMessage: (conversationId, message) => {
    const conversations = get().conversations.map((c) =>
      c.id === conversationId
        ? { ...c, messages: [...c.messages, message], updatedAt: Date.now() }
        : c
    );
    set({ conversations });
    saveConversations(conversations);
  },

  updateLastAssistantMessage: (conversationId, content) => {
    const conversations = get().conversations.map((c) => {
      if (c.id !== conversationId) return c;
      const msgs = [...c.messages];
      const lastIdx = msgs.length - 1;
      if (lastIdx >= 0 && msgs[lastIdx].role === "assistant") {
        msgs[lastIdx] = { ...msgs[lastIdx], content, isStreaming: true };
      }
      return { ...c, messages: msgs, updatedAt: Date.now() };
    });
    set({ conversations });
  },

  finalizeAssistantMessage: (conversationId, content) => {
    const s = get();
    const toolCallsSnapshot = s.toolCalls;
    const dataPreviewSnapshot = s.dataPreview;
    const sourceCitationsSnapshot = s.sourceCitations;
    const lastToolsUsedSnapshot = s.lastToolsUsed;

    const conversations = s.conversations.map((c) => {
      if (c.id !== conversationId) return c;
      const msgs = [...c.messages];
      const lastIdx = msgs.length - 1;
      if (lastIdx >= 0 && msgs[lastIdx].role === "assistant") {
        msgs[lastIdx] = {
          ...msgs[lastIdx],
          content,
          isStreaming: false,
          toolCalls: [...toolCallsSnapshot],
          dataPreview: dataPreviewSnapshot ? { ...dataPreviewSnapshot } : null,
          sourceCitations: [...sourceCitationsSnapshot],
          lastToolsUsed: [...lastToolsUsedSnapshot],
        };
      }
      return { ...c, messages: msgs, updatedAt: Date.now() };
    });
    set({ conversations });
    saveConversations(conversations);
  },

  // ── UI ───────────────────────────────────────────────────────

  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleRightPanel: () => set((s) => ({ rightPanelOpen: !s.rightPanelOpen })),
  setRightPanelOpen: (open) => set({ rightPanelOpen: open }),

  toggleTheme: () => {
    const next: ThemeValue = get().theme === "dark" ? "light" : "dark";
    saveTheme(next);
    applyTheme(next);
    set({ theme: next });
  },

  // ── Streaming ────────────────────────────────────────────────

  setStreaming: (streaming) => set({ isStreaming: streaming }),

  setStreamingContent: (content) => set({ streamingContent: content }),

  appendStreamingContent: (token) =>
    set((s) => ({ streamingContent: s.streamingContent + token })),

  // ── Analysis ─────────────────────────────────────────────────

  addToolCall: (toolCall) =>
    set((s) => ({ toolCalls: [...s.toolCalls, toolCall] })),

  updateToolCall: (tool, update) =>
    set((s) => ({
      toolCalls: s.toolCalls.map((tc) =>
        tc.tool === tool ? { ...tc, ...update } : tc
      ),
    })),

  clearAnalysis: () =>
    set({
      toolCalls: [],
      dataPreview: null,
      sourceCitations: [],
      lastToolsUsed: [],
      streamingContent: "",
    }),

  setDataPreview: (preview) => set({ dataPreview: preview }),

  addCitation: (citation) =>
    set((s) => ({ sourceCitations: [...s.sourceCitations, citation] })),

  setLastToolsUsed: (tools) => set({ lastToolsUsed: tools }),

  // ── Error ────────────────────────────────────────────────────

  setConnectionError: (error) => set({ connectionError: error }),

  // ── Computed ─────────────────────────────────────────────────

  getActiveConversation: () => {
    const { conversations, activeConversationId } = get();
    return conversations.find((c) => c.id === activeConversationId);
  },
}));
