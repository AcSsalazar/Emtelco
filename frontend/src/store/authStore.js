import { create } from "zustand";
import { persist } from "zustand/middleware";

export const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      access: null,
      refresh: null,
      setSession: ({ user, access, refresh }) => set({ user, access, refresh }),
      clear: () => set({ user: null, access: null, refresh: null }),
    }),
    { name: "emtelco-auth" }
  )
);
