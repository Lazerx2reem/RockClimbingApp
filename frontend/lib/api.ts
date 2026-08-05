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
  VideoDetail,
  VideoSummary,
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

/** Extract a human-readable message from a failed response (FastAPI shapes). */
async function toApiError(res: Response): Promise<ApiError> {
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
  return new ApiError(res.status, message);
}

/** Handle the shared 401 -> logout redirect. Returns true if it acted. */
function handleUnauthorized(res: Response, path: string): boolean {
  if (res.status === 401 && !path.startsWith("/auth/login")) {
    clearToken();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    return true;
  }
  return false;
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

  if (handleUnauthorized(res, path)) {
    throw new ApiError(401, "Session expired. Please log in again.");
  }
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  return res.json();
}

/** Multipart POST (file uploads). Lets the browser set the boundary. */
async function upload<T>(path: string, form: FormData): Promise<T> {
  const token = getToken();
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
  } catch {
    throw new ApiError(0, "Cannot reach the Ascent API. Is the backend running?");
  }
  if (handleUnauthorized(res, path)) {
    throw new ApiError(401, "Session expired. Please log in again.");
  }
  if (!res.ok) throw await toApiError(res);
  return res.json();
}

/** Fetch an authorized binary resource as an object URL, or null if absent. */
async function fetchObjectUrl(path: string): Promise<string | null> {
  const token = getToken();
  const res = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) return null;
  return URL.createObjectURL(await res.blob());
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

  listVideos: () => request<VideoSummary[]>("/videos"),
  getVideo: (id: number) => request<VideoDetail>(`/videos/${id}`),
  uploadVideo: (file: File, climbId?: number) => {
    const form = new FormData();
    form.append("file", file);
    if (climbId != null) form.append("climb_id", String(climbId));
    return upload<VideoSummary>("/videos", form);
  },
  createSampleVideo: (skill?: number) =>
    request<VideoDetail>(
      `/videos/sample${skill != null ? `?skill=${skill}` : ""}`,
      { method: "POST" }
    ),
  reanalyzeVideo: (id: number) =>
    request<VideoSummary>(`/videos/${id}/reanalyze`, { method: "POST" }),
  deleteVideo: (id: number) => request<void>(`/videos/${id}`, { method: "DELETE" }),
  videoFileUrl: (id: number) => fetchObjectUrl(`/videos/${id}/file`),
};
