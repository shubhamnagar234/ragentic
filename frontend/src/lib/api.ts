const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Server-side fetch helper
// Used in Server Components and API routes
export async function serverFetch(
  path: string,
  options: RequestInit = {},
  token?: string,
) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// Client-side fetch helper
// Calls Next.js API routes (not FastAPI directly)
export async function clientFetch(path: string, options: RequestInit = {}) {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// Workspace API (client-side)
export const workspaceApi = {
  getAll: () => clientFetch("/workspaces"),
  getOne: (id: string) => clientFetch(`/workspaces/${id}`),
  create: (name: string) =>
    clientFetch("/workspaces", {
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
};

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
  delete: (workspaceId: string, sourceId: string) =>
    clientFetch(`/workspaces/${workspaceId}/sources/${sourceId}`, {
      method: "DELETE",
    }),
};

// Analytics API (client-side)
export const analyticsApi = {
  getMetrics: (workspaceId: string) =>
    clientFetch(`/workspaces/${workspaceId}/analytics`),
  getScoreTrend: (workspaceId: string) =>
    clientFetch(`/workspaces/${workspaceId}/analytics/scores`),
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
      source_ids: sourceIds.length > 0 ? sourceIds : null,
    }),
  });
};
