"use client";

import { useState, type FormEvent } from "react";
import {
  createWorkspaceAction,
  deleteWorkspaceAction,
  renameWorkspaceAction,
} from "@/app/dashboard/actions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { Workspace } from "@/lib/api";

const inputClassName =
  "rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

export function WorkspaceManager({
  initialWorkspaces,
  initialError,
}: {
  initialWorkspaces: Workspace[];
  initialError: string | null;
}) {
  const [workspaces, setWorkspaces] = useState(initialWorkspaces);
  const [selectedId, setSelectedId] = useState<string | null>(
    initialWorkspaces[0]?.id ?? null
  );
  const [error, setError] = useState<string | null>(initialError);

  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const selected = workspaces.find((workspace) => workspace.id === selectedId) ?? null;

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    const name = newName.trim();
    if (!name) return;

    setCreating(true);
    setError(null);
    const result = await createWorkspaceAction(name);
    setCreating(false);

    if (!result.ok) {
      setError(result.message);
      return;
    }
    setWorkspaces((prev) => [result.data, ...prev]);
    setSelectedId(result.data.id);
    setNewName("");
  }

  async function handleRename(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;

    const formData = new FormData(event.currentTarget);
    const name = String(formData.get("name") ?? "").trim();
    if (!name) return;

    setRenaming(true);
    setError(null);
    const result = await renameWorkspaceAction(selected.id, name);
    setRenaming(false);

    if (!result.ok) {
      setError(result.message);
      return;
    }
    setWorkspaces((prev) =>
      prev.map((workspace) => (workspace.id === result.data.id ? result.data : workspace))
    );
  }

  async function handleDelete() {
    if (!selected) return;

    setDeleting(true);
    setError(null);
    const result = await deleteWorkspaceAction(selected.id);
    setDeleting(false);
    setConfirmingDelete(false);

    if (!result.ok) {
      setError(result.message);
      return;
    }
    const remaining = workspaces.filter((workspace) => workspace.id !== selected.id);
    setWorkspaces(remaining);
    setSelectedId(remaining[0]?.id ?? null);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Workspaces</CardTitle>
        <CardDescription>
          A workspace isolates your documents, complaints, and tasks from other workspaces.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {error && <p className="text-sm text-destructive">{error}</p>}

        <form onSubmit={handleCreate} className="flex gap-2">
          <input
            value={newName}
            onChange={(event) => setNewName(event.target.value)}
            placeholder="New workspace name"
            className={`${inputClassName} flex-1`}
          />
          <Button type="submit" disabled={creating || !newName.trim()}>
            {creating ? "Creating..." : "Create workspace"}
          </Button>
        </form>

        {workspaces.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            You don&apos;t have any workspaces yet. Create one above to get started.
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-[200px_1fr]">
            <ul className="flex flex-col gap-1">
              {workspaces.map((workspace) => (
                <li key={workspace.id}>
                  <Button
                    type="button"
                    variant={workspace.id === selectedId ? "secondary" : "ghost"}
                    className="w-full justify-start"
                    onClick={() => {
                      setSelectedId(workspace.id);
                      setConfirmingDelete(false);
                    }}
                  >
                    {workspace.name}
                  </Button>
                </li>
              ))}
            </ul>

            {selected && (
              <div className="flex flex-col gap-3 rounded-xl border p-4">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium">{selected.name}</h3>
                  <Badge variant="outline">{selected.role}</Badge>
                </div>
                <dl className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="text-muted-foreground">Created</dt>
                    <dd>{new Date(selected.created_at).toLocaleString()}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Updated</dt>
                    <dd>{new Date(selected.updated_at).toLocaleString()}</dd>
                  </div>
                </dl>

                <form key={selected.id} onSubmit={handleRename} className="flex gap-2">
                  <input
                    name="name"
                    defaultValue={selected.name}
                    className={`${inputClassName} flex-1`}
                  />
                  <Button type="submit" disabled={renaming}>
                    {renaming ? "Saving..." : "Save name"}
                  </Button>
                </form>

                <div>
                  {!confirmingDelete ? (
                    <Button
                      type="button"
                      variant="destructive"
                      onClick={() => setConfirmingDelete(true)}
                    >
                      Delete workspace
                    </Button>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">
                        Delete this workspace?
                      </span>
                      <Button
                        type="button"
                        variant="destructive"
                        disabled={deleting}
                        onClick={handleDelete}
                      >
                        {deleting ? "Deleting..." : "Confirm"}
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => setConfirmingDelete(false)}
                      >
                        Cancel
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
