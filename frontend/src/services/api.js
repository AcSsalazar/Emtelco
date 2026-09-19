import axios from "axios";
import { useAuthStore } from "../store/authStore";

export const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().access;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshRequest = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const { access, refresh, user, setSession, clear } = useAuthStore.getState();

    if (
      error.response?.status === 401 &&
      access &&
      refresh &&
      original &&
      !original._retry
    ) {
      original._retry = true;
      try {
        refreshRequest =
          refreshRequest || axios.post("/api/auth/refresh", { refresh });
        const { data } = await refreshRequest;
        refreshRequest = null;
        setSession({ user, access: data.access, refresh: data.refresh || refresh });
        original.headers.Authorization = `Bearer ${data.access}`;
        return api(original);
      } catch (refreshError) {
        refreshRequest = null;
        clear();
      }
    }

    return Promise.reject(error);
  }
);

export function apiErrorMessage(error) {
  const data = error?.response?.data;
  if (typeof data?.detail === "string") return data.detail;
  if (data && typeof data === "object") {
    const first = Object.values(data)[0];
    if (Array.isArray(first)) return String(first[0]);
    if (typeof first === "string") return first;
  }
  return "Ocurrió un error. Intenta nuevamente.";
}
