/**
 * Application constants.
 */

export const APP_NAME = "wireframe";
export const APP_DESCRIPTION =
  "Agentic parser and EDA tool for integrated circuit reference designs";

// API Routes (all prefixed with /api/v1 via api-client)
export const API_ROUTES = {
  // Auth
  LOGIN: "/auth/login",
  REGISTER: "/auth/register",
  LOGOUT: "/auth/logout",
  REFRESH: "/auth/refresh",
  ME: "/auth/me",

  // Health
  HEALTH: "/health",

  // Users
  USERS: "/users",

  // Chat (AI Agent)
  CHAT: "/chat",

  // EDA Workflows (adjust these to match your backend routes)
  ANALYZE: "/analyze",
  JOBS: "/jobs",
  AGENT: "/agent",
} as const;

// Navigation routes
export const ROUTES = {
  HOME: "/",
  LOGIN: "/login",
  REGISTER: "/register",
  DASHBOARD: "/dashboard",
  CHAT: "/chat",
  EDITOR: "/editor",
  JOBS: "/jobs",
  PROFILE: "/profile",
  SETTINGS: "/settings",
} as const;

// API and WebSocket URLs (Vite env variables)
export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8080";
export const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8080";
