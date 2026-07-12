import { SignJWT } from "jose";

const API_URL = process.env.NEXT_PUBLIC_API_URL as string;

export async function generateToken(userId: string): Promise<string> {
  const secret = new TextEncoder().encode(process.env.AUTH_SECRET);

  return new SignJWT({ sub: userId })
    .setProtectedHeader({ alg: "HS256" })
    .setExpirationTime("7d")
    .sign(secret);
}

// Custom error class that carries the upstream HTTP status code
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Server-side fetch helper
// Used in Server Components and API routes
export async function serverFetch(
  path: string,
  options: RequestInit = {},
  userId?: string,
) {
  const isFormData = options.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers as Record<string, string>),
  }

  if (userId) {
    const token = await generateToken(userId)
    headers["Authorization"] = `Bearer ${token}`
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const body = await response.text().catch(() => "")
    throw new ApiError(
      response.status,
      `API error ${response.status}: ${response.statusText}${body ? ` — ${body}` : ""}`,
    )
  }

  // Handle empty responses (204 No Content)
  if (response.status === 204 || response.headers.get("content-length") === "0") {
    return null
  }

  const text = await response.text()
  if (!text) return null

  return JSON.parse(text)
}




// Client-side fetch helper
// Calls Next.js API routes (not FastAPI directly)
export async function clientFetch(
  path: string,
  options: RequestInit = {},
) {
  const isFormData = options.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers as Record<string, string>),
  };

  const response = await fetch(`/api${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`)
  }

  // Handle empty responses (204 No Content)
  if (response.status === 204 || response.headers.get("content-length") === "0") {
    return null
  }

  const text = await response.text()
  if (!text) return null

  return JSON.parse(text)
}

// Workspace API (client-side)
export const workspaceApi = {
  getAll: () => clientFetch("/workspaces/"),
  getOne: (id: string) => clientFetch(`/workspaces/${id}`),
  create: (name: string) =>
    clientFetch("/workspaces/", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  update: (id: string, name: string) =>
    clientFetch(`/workspaces/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),
  delete: (id: string) =>
    clientFetch(`/workspaces/${id}`, { method: "DELETE" }),
}

// Sources API (client-side)
export const sourcesApi = {
  getAll: (workspaceId: string) =>
    clientFetch(`/workspaces/${workspaceId}/sources`),
  getOne: (workspaceId: string, sourceId: string) =>
    clientFetch(`/workspaces/${workspaceId}/sources/${sourceId}`),
  create: (
    workspaceId: string,
    data: { url?: string; source_type: string; title?: string },
  ) =>
    clientFetch(`/workspaces/${workspaceId}/sources`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  upload: (workspaceId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return clientFetch(`/workspaces/${workspaceId}/sources/upload`, {
      method: "POST",
      body: formData,
    });
  },
  delete: (workspaceId: string, sourceId: string) =>
    clientFetch(`/workspaces/${workspaceId}/sources/${sourceId}`, {
      method: "DELETE",
    }),
  retry: (workspaceId: string, sourceId: string) =>
    clientFetch(`/workspaces/${workspaceId}/sources/${sourceId}/retry`, {
      method: "POST",
    }),
};

// Analytics API (client-side)
export const analyticsApi = {
  getMetrics: (workspaceId: string) =>
    clientFetch(`/workspaces/${workspaceId}/analytics`),
  getScoreTrend: (workspaceId: string) =>
    clientFetch(`/workspaces/${workspaceId}/analytics/scores`),
}

// Sessions API (client-side)
export const sessionsApi = {
  getAll: (workspaceId: string) =>
    clientFetch(`/workspaces/${workspaceId}/sessions`),
  create: (workspaceId: string, title: string) =>
    clientFetch(`/workspaces/${workspaceId}/sessions`, {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  delete: (workspaceId: string, sessionId: string) =>
    clientFetch(`/workspaces/${workspaceId}/sessions/${sessionId}`, {
      method: "DELETE",
    }),
};

// Reports API (client-side)
export const reportsApi = {
  getAll: (workspaceId: string) =>
    clientFetch(`/workspaces/${workspaceId}/reports`),
  getOne: (workspaceId: string, reportId: string) =>
    clientFetch(`/workspaces/${workspaceId}/reports/${reportId}`),
  delete: (workspaceId: string, reportId: string) =>
    clientFetch(`/workspaces/${workspaceId}/reports/${reportId}`, {
      method: "DELETE",
    }),
};

// SSE Chat stream (client-side)
// Goes through Next.js API route which attaches token server-side
export const createChatStream = (
  workspaceId: string,
  sessionId: string | null,
  query: string,
  sourceIds: string[],
) => {
  return fetch(`/api/workspaces/${workspaceId}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query,
      workspace_id: workspaceId,
      session_id: sessionId,
      source_ids: sourceIds.length > 0 ? sourceIds : null,
    }),
  });
};

// Messages API (client-side)
export const messagesApi = {
  getAll: (workspaceId: string, sessionId?: string | null) => {
    const url = sessionId 
      ? `/workspaces/${workspaceId}/messages?session_id=${sessionId}`
      : `/workspaces/${workspaceId}/messages`;
    return clientFetch(url);
  },
  deleteAll: (workspaceId: string, sessionId?: string | null) => {
    const url = sessionId
      ? `/workspaces/${workspaceId}/messages?session_id=${sessionId}`
      : `/workspaces/${workspaceId}/messages`;
    return clientFetch(url, { method: "DELETE" });
  },
  submitFeedback: (workspaceId: string, messageId: string, feedback: "UP" | "DOWN" | null) =>
    clientFetch(`/workspaces/${workspaceId}/messages/${messageId}/feedback`, {
      method: "PATCH",
      body: JSON.stringify({ feedback }),
    }),
};
