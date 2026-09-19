import { create } from "zustand";
import { api } from "../services/api";

export const useProfileStore = create((set) => ({
  profile: null,
  loadProfile: async () => {
    try {
      const { data } = await api.get("/profile");
      set({ profile: data });
    } catch {
      // Profile is optional for the chat; ignore failures.
    }
  },
  reset: () => set({ profile: null }),
}));
