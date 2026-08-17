"use server";

import {
  createWorkspace,
  deleteDocument,
  deleteWorkspace,
  listDocuments,
  updateWorkspace,
  uploadDocument,
  type Document,
  type Workspace,
} from "@/lib/api";
import { createClient } from "@/lib/supabase/server";

type ActionResult<T> = { ok: true; data: T } | { ok: false; message: string };

async function getAccessToken(): Promise<string | null> {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

export async function createWorkspaceAction(name: string): Promise<ActionResult<Workspace>> {
  const accessToken = await getAccessToken();
  if (!accessToken) {
    return { ok: false, message: "Your session has expired. Please log in again." };
  }

  const result = await createWorkspace(accessToken, name);
  if (!result.ok) {
    return { ok: false, message: result.message };
  }
  return { ok: true, data: result.data };
}

export async function renameWorkspaceAction(
  workspaceId: string,
  name: string
): Promise<ActionResult<Workspace>> {
  const accessToken = await getAccessToken();
  if (!accessToken) {
    return { ok: false, message: "Your session has expired. Please log in again." };
  }

  const result = await updateWorkspace(accessToken, workspaceId, name);
  if (!result.ok) {
    return { ok: false, message: result.message };
  }
  return { ok: true, data: result.data };
}

export async function deleteWorkspaceAction(
  workspaceId: string
): Promise<ActionResult<null>> {
  const accessToken = await getAccessToken();
  if (!accessToken) {
    return { ok: false, message: "Your session has expired. Please log in again." };
  }

  const result = await deleteWorkspace(accessToken, workspaceId);
  if (!result.ok) {
    return { ok: false, message: result.message };
  }
  return { ok: true, data: null };
}

export async function listDocumentsAction(
  workspaceId: string
): Promise<ActionResult<Document[]>> {
  const accessToken = await getAccessToken();
  if (!accessToken) {
    return { ok: false, message: "Your session has expired. Please log in again." };
  }

  const result = await listDocuments(accessToken, workspaceId);
  if (!result.ok) {
    return { ok: false, message: result.message };
  }
  return { ok: true, data: result.data };
}

export async function uploadDocumentAction(
  workspaceId: string,
  formData: FormData
): Promise<ActionResult<Document>> {
  const accessToken = await getAccessToken();
  if (!accessToken) {
    return { ok: false, message: "Your session has expired. Please log in again." };
  }

  const file = formData.get("file");
  if (!(file instanceof File) || file.size === 0) {
    return { ok: false, message: "Choose a file to upload." };
  }

  const result = await uploadDocument(accessToken, workspaceId, file);
  if (!result.ok) {
    return { ok: false, message: result.message };
  }
  return { ok: true, data: result.data };
}

export async function deleteDocumentAction(
  workspaceId: string,
  documentId: string
): Promise<ActionResult<null>> {
  const accessToken = await getAccessToken();
  if (!accessToken) {
    return { ok: false, message: "Your session has expired. Please log in again." };
  }

  const result = await deleteDocument(accessToken, workspaceId, documentId);
  if (!result.ok) {
    return { ok: false, message: result.message };
  }
  return { ok: true, data: null };
}
