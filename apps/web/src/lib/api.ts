export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
}

export type HealthResult =
  | { ok: true; data: HealthResponse }
  | { ok: false };

const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";
const HEALTH_TIMEOUT_MS = 3000;

export async function getHealth(): Promise<HealthResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(HEALTH_TIMEOUT_MS),
    });

    if (!response.ok) {
      return { ok: false };
    }

    const data = (await response.json()) as HealthResponse;
    return { ok: true, data };
  } catch {
    return { ok: false };
  }
}

export interface MeResponse {
  id: string;
}

export type MeResult = { ok: true; data: MeResponse } | { ok: false };

export async function getMe(accessToken: string): Promise<MeResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/me`, {
      cache: "no-store",
      headers: { Authorization: `Bearer ${accessToken}` },
      signal: AbortSignal.timeout(HEALTH_TIMEOUT_MS),
    });

    if (!response.ok) {
      return { ok: false };
    }

    const data = (await response.json()) as MeResponse;
    return { ok: true, data };
  } catch {
    return { ok: false };
  }
}

export interface Workspace {
  id: string;
  name: string;
  role: string;
  created_at: string;
  updated_at: string;
}

export type WorkspaceApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; status: number; message: string };

const WORKSPACE_TIMEOUT_MS = 5000;

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      const firstError = body.detail[0] as { msg?: string };
      if (typeof firstError.msg === "string") {
        return firstError.msg;
      }
    }
  } catch {
    // response body wasn't JSON — fall through to the generic message below
  }
  return `Request failed (${response.status})`;
}

async function workspaceRequest<T>(
  path: string,
  accessToken: string,
  init?: RequestInit
): Promise<WorkspaceApiResult<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      cache: "no-store",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
      },
      signal: AbortSignal.timeout(WORKSPACE_TIMEOUT_MS),
    });

    if (!response.ok) {
      return { ok: false, status: response.status, message: await extractErrorMessage(response) };
    }

    if (response.status === 204) {
      return { ok: true, data: undefined as T };
    }

    const data = (await response.json()) as T;
    return { ok: true, data };
  } catch {
    return { ok: false, status: 0, message: "Could not reach the backend." };
  }
}

export async function listWorkspaces(
  accessToken: string
): Promise<WorkspaceApiResult<Workspace[]>> {
  return workspaceRequest<Workspace[]>("/workspaces", accessToken);
}

export async function createWorkspace(
  accessToken: string,
  name: string
): Promise<WorkspaceApiResult<Workspace>> {
  return workspaceRequest<Workspace>("/workspaces", accessToken, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function updateWorkspace(
  accessToken: string,
  workspaceId: string,
  name: string
): Promise<WorkspaceApiResult<Workspace>> {
  return workspaceRequest<Workspace>(`/workspaces/${workspaceId}`, accessToken, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

export async function deleteWorkspace(
  accessToken: string,
  workspaceId: string
): Promise<WorkspaceApiResult<null>> {
  return workspaceRequest<null>(`/workspaces/${workspaceId}`, accessToken, {
    method: "DELETE",
  });
}

export interface Document {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

const UPLOAD_TIMEOUT_MS = 20000;

export async function listDocuments(
  accessToken: string,
  workspaceId: string
): Promise<WorkspaceApiResult<Document[]>> {
  return workspaceRequest<Document[]>(`/workspaces/${workspaceId}/documents`, accessToken);
}

export async function uploadDocument(
  accessToken: string,
  workspaceId: string,
  file: File
): Promise<WorkspaceApiResult<Document>> {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(`${API_BASE_URL}/workspaces/${workspaceId}/documents`, {
      method: "POST",
      cache: "no-store",
      headers: { Authorization: `Bearer ${accessToken}` },
      body: formData,
      signal: AbortSignal.timeout(UPLOAD_TIMEOUT_MS),
    });

    if (!response.ok) {
      return { ok: false, status: response.status, message: await extractErrorMessage(response) };
    }

    const data = (await response.json()) as Document;
    return { ok: true, data };
  } catch {
    return { ok: false, status: 0, message: "Could not reach the backend." };
  }
}

export async function deleteDocument(
  accessToken: string,
  workspaceId: string,
  documentId: string
): Promise<WorkspaceApiResult<null>> {
  return workspaceRequest<null>(`/workspaces/${workspaceId}/documents/${documentId}`, accessToken, {
    method: "DELETE",
  });
}
