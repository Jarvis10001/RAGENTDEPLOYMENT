/**
 * localStorage helpers for conversations and theme persistence.
 */

import type { Conversation, Message } from "../store/useStore";

const CONVERSATIONS_KEY = "ri_conversations";
const THEME_KEY = "ri_theme";

export type ThemeValue = "dark" | "light";

// ── Conversations ────────────────────────────────────────────────

export function loadConversations(): Conversation[] {
  try {
    const raw = localStorage.getItem(CONVERSATIONS_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed as Conversation[];
  } catch {
    return [];
  }
}

export function saveConversations(conversations: Conversation[]): void {
  try {
    localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(conversations));
  } catch {
    // localStorage full — silently fail
  }
}

export function deleteConversation(id: string): Conversation[] {
  const conversations = loadConversations().filter((c) => c.id !== id);
  saveConversations(conversations);
  return conversations;
}

export function saveConversation(conversation: Conversation): void {
  const conversations = loadConversations();
  const idx = conversations.findIndex((c) => c.id === conversation.id);
  if (idx >= 0) {
    conversations[idx] = conversation;
  } else {
    conversations.unshift(conversation);
  }
  saveConversations(conversations);
}

export function addMessageToConversation(
  conversationId: string,
  message: Message
): void {
  const conversations = loadConversations();
  const conv = conversations.find((c) => c.id === conversationId);
  if (conv) {
    conv.messages.push(message);
    conv.updatedAt = Date.now();
    saveConversations(conversations);
  }
}

// ── Theme ────────────────────────────────────────────────────────

export function loadTheme(): ThemeValue {
  try {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === "light" || stored === "dark") return stored;
    return "dark";
  } catch {
    return "dark";
  }
}

export function saveTheme(theme: ThemeValue): void {
  try {
    localStorage.setItem(THEME_KEY, theme);
    document.documentElement.setAttribute("data-theme", theme);
  } catch {
    // silently fail
  }
}

export function applyTheme(theme: ThemeValue): void {
  document.documentElement.setAttribute("data-theme", theme);
}
