import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api, apiErrorMessage } from "../services/api";

export const useChatStore = create(
  persist(
    (set, get) => ({
      conversations: [],
      conversationId: null,
      messages: [],
      loadingConversation: false,
      sending: false,
      error: null,
      escalated: false,
      // True when the last stored message is a user message without a reply
      // (e.g. the page was refreshed while the agent was responding).
      pendingReply: false,

      loadConversations: async () => {
        const { data } = await api.get("/conversations");
        const list = data.results ?? data;
        set({ conversations: list });
        return list;
      },

      // Restore the session after a reload: reopen the last conversation, or
      // the most recent one, or start a draft (no empty conversations created).
      bootstrap: async () => {
        const list = await get().loadConversations();
        const storedId = get().conversationId;
        if (storedId && list.some((item) => item.id === storedId)) {
          await get().openConversation(storedId);
          return;
        }
        if (list.length > 0) {
          await get().openConversation(list[0].id);
          return;
        }
        set({ conversationId: null, messages: [], pendingReply: false, error: null });
      },

      startNewConversation: async () => {
        const empty = get().conversations.find((item) => item.message_count === 0);
        if (empty) {
          await get().openConversation(empty.id);
          return;
        }
        set({
          conversationId: null,
          messages: [],
          escalated: false,
          pendingReply: false,
          error: null,
        });
      },

      selectConversation: async (id) => {
        if (id !== get().conversationId) {
          await get().openConversation(id);
        }
      },

      createConversation: async () => {
        const { data } = await api.post("/conversations", {});
        set((state) => ({
          conversations: [data, ...state.conversations],
          conversationId: data.id,
          messages: [],
          escalated: data.escalated,
          pendingReply: false,
          error: null,
        }));
        return data;
      },

      openConversation: async (id) => {
        set({
          conversationId: id,
          loadingConversation: true,
          error: null,
          pendingReply: false,
        });
        try {
          const { data } = await api.get(`/conversations/${id}`);
          const messages = data.messages ?? [];
          const last = messages[messages.length - 1];
          set({
            messages,
            escalated: data.escalated,
            loadingConversation: false,
            pendingReply: Boolean(last && last.role === "user"),
          });
        } catch (error) {
          set({ loadingConversation: false, error: "No pude cargar la conversación." });
        }
      },

      sendMessage: async (content) => {
        if (!content.trim()) return;

        let id = get().conversationId;
        if (!id) {
          const created = await get().createConversation();
          id = created.id;
        }

        const optimistic = {
          id: `tmp-${Date.now()}`,
          role: "user",
          content,
          created_at: new Date().toISOString(),
        };
        set((state) => ({
          messages: [...state.messages, optimistic],
          sending: true,
          error: null,
          pendingReply: false,
        }));

        try {
          const { data } = await api.post(`/conversations/${id}/messages`, { content });
          set((state) => ({
            messages: [
              ...state.messages,
              {
                id: `assistant-${Date.now()}`,
                role: "assistant",
                content: data.reply,
                created_at: new Date().toISOString(),
              },
            ],
            sending: false,
            escalated: data.escalated,
          }));
          get()._touchConversation(id, 2);
        } catch (error) {
          set({ sending: false, error: apiErrorMessage(error) });
        }
      },

      retryPendingReply: async () => {
        const id = get().conversationId;
        if (!id) return;
        set({ sending: true, error: null });
        try {
          const { data } = await api.post(`/conversations/${id}/messages`, {
            retry: true,
          });
          set((state) => ({
            messages: [
              ...state.messages,
              {
                id: `assistant-${Date.now()}`,
                role: "assistant",
                content: data.reply,
                created_at: new Date().toISOString(),
              },
            ],
            sending: false,
            pendingReply: false,
            escalated: data.escalated,
          }));
          get()._touchConversation(id, 1);
        } catch (error) {
          set({ sending: false, error: apiErrorMessage(error) });
        }
      },

      _touchConversation: (id, increment) => {
        set((state) => {
          const target = state.conversations.find((item) => item.id === id);
          if (!target) return {};
          const updated = {
            ...target,
            message_count: (target.message_count || 0) + increment,
            updated_at: new Date().toISOString(),
          };
          const rest = state.conversations.filter((item) => item.id !== id);
          return { conversations: [updated, ...rest] };
        });
      },

      reset: () =>
        set({
          conversations: [],
          conversationId: null,
          messages: [],
          error: null,
          escalated: false,
          pendingReply: false,
        }),
    }),
    {
      name: "emtelco-chat",
      partialize: (state) => ({ conversationId: state.conversationId }),
    }
  )
);
