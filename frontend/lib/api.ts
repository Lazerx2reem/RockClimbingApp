import { clearToken, getToken } from "./token";
import type {
  AngleEntry,
  Climb,
  ClimbCreate,
  ProgressPoint,
  PyramidEntry,
  SessionCreate,
  StatsSummary,
  TrainingSession,
  UserProfile,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(0, "Cannot reach the Ascent API. Is the backend running?");
  }

  if (res.status === 401 && !path.startsWith("/auth/login")) {
    clearToken();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new ApiError(401, "Session expired. Please log in again.");
  }

  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) {
        message = body.detail
          .map((d: { loc?: unknown[]; msg?: string }) =>
            `${(d.loc ?? []).slice(1).join(".")}: ${d.msg ?? "invalid"}`
          )
          .join("; ");
      }
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  register: (email: string, password: string, displayName: string) =>
    request<{ access_token: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, display_name: displayName }),
    }),
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<UserProfile>("/auth/me"),
  updateProfile: (patch: Partial<UserProfile>) =>
    request<UserProfile>("/auth/me", { method: "PATCH", body: JSON.stringify(patch) }),

  listClimbs: () => request<Climb[]>("/climbs"),
  createClimb: (climb: ClimbCreate) =>
    request<Climb>("/climbs", { method: "POST", body: JSON.stringify(climb) }),
  deleteClimb: (id: number) => request<void>(`/climbs/${id}`, { method: "DELETE" }),

  listSessions: () => request<TrainingSession[]>("/sessions"),
  createSession: (session: SessionCreate) =>
    request<TrainingSession>("/sessions", {
      method: "POST",
      body: JSON.stringify(session),
    }),
  deleteSession: (id: number) => request<void>(`/sessions/${id}`, { method: "DELETE" }),

  pyramid: (discipline: "boulder" | "route") =>
    request<PyramidEntry[]>(`/stats/pyramid?discipline=${discipline}`),
  progress: () => request<ProgressPoint[]>("/stats/progress"),
  angles: () => request<AngleEntry[]>("/stats/angles"),
  summary: () => request<StatsSummary>("/stats/summary"),
};
