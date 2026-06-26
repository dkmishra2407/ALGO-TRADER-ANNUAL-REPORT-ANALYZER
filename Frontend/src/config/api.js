const DEFAULT_API_BASE_URL = "http://localhost:8000";

/** Backend API base URL (no trailing slash). Set VITE_API_BASE_URL at build time. */
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL)
  .trim()
  .replace(/\/+$/, "");
