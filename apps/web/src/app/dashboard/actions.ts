"use server";

import { createWorkspace, deleteWorkspace, updateWorkspace, type Workspace } from "@/lib/api";
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
