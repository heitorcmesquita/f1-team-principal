import axios from "axios";

export const api = axios.create({
  // Dev: Vite proxies /api -> the FastAPI backend (strips the /api prefix).
  // Prod: the backend serves the built SPA and the API on the same origin, so
  // request paths like "/race/teams" must resolve as-is (no extra prefix).
  baseURL: import.meta.env.PROD ? "" : "/api",
});