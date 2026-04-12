/**
 * Conversation management hook — CRUD operations on conversations.
 */

import { useCallback } from "react";
import { useStore, createConversation } from "../store/useStore";
import { clearSession } from "../lib/api";

interface UseConversationReturn {
  conversations: ReturnType<typeof useStore.getState>["conversations"];
  activeConversationId: string | null;
  createNew: () => void;
  switchTo: (id: string) => void;
  remove: (id: string) => void;
  rename: (id: string, title: string) => void;
  exportConversation: () => void;
}

function groupByDate(
  conversations: ReturnType<typeof useStore.getState>["conversations"]
): {
  today: typeof conversations;
  yesterday: typeof conversations;
  older: typeof conversations;
} {
  const now = new Date();
  const todayStart = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate()
  ).getTime();
  const yesterdayStart = todayStart - 86_400_000;

  const today = conversations.filter((c) => c.updatedAt >= todayStart);
  const yesterday = conversations.filter(
    (c) => c.updatedAt >= yesterdayStart && c.updatedAt < todayStart
  );
  const older = conversations.filter((c) => c.updatedAt < yesterdayStart);

  return { today, yesterday, older };
}

export { groupByDate };

export function useConversation(): UseConversationReturn {
  const conversations = useStore((s) => s.conversations);
  const activeConversationId = useStore((s) => s.activeConversationId);
  const addConversation = useStore((s) => s.addConversation);
  const deleteConversation = useStore((s) => s.deleteConversation);
  const setActiveConversation = useStore((s) => s.setActiveConversation);
  const updateConversationTitle = useStore((s) => s.updateConversationTitle);

  const createNew = useCallback(() => {
    const conv = createConversation("New conversation");
    addConversation(conv);
  }, [addConversation]);

  const switchTo = useCallback(
    (id: string) => {
      setActiveConversation(id);
    },
    [setActiveConversation]
  );

  const remove = useCallback(
    (id: string) => {
      deleteConversation(id);
      // Also clear server-side session
      clearSession(id).catch(() => {
        // silently fail
      });
    },
    [deleteConversation]
  );

  const rename = useCallback(
    (id: string, title: string) => {
      updateConversationTitle(id, title);
    },
    [updateConversationTitle]
  );

  const exportConversation = useCallback(() => {
    const conv = conversations.find((c) => c.id === activeConversationId);
    if (!conv) return;

    const text = conv.messages
      .map((m) => `[${m.role.toUpperCase()}]\n${m.content}\n`)
      .join("\n---\n\n");

    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${conv.title.replace(/[^a-zA-Z0-9]/g, "_")}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }, [conversations, activeConversationId]);

  return {
    conversations,
    activeConversationId,
    createNew,
    switchTo,
    remove,
    rename,
    exportConversation,
  };
}
