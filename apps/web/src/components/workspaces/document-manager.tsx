"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  deleteDocumentAction,
  listDocumentsAction,
  uploadDocumentAction,
} from "@/app/dashboard/actions";
import { Button } from "@/components/ui/button";
import type { Document } from "@/lib/api";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentManager({ workspaceId }: { workspaceId: string }) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    let cancelled = false;
    listDocumentsAction(workspaceId).then((result) => {
      if (cancelled) return;
      setLoading(false);
      if (!result.ok) {
        setError(result.message);
        return;
      }
      setDocuments(result.data);
    });
    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);

    setUploading(true);
    setError(null);
    const result = await uploadDocumentAction(workspaceId, formData);
    setUploading(false);

    if (!result.ok) {
      setError(result.message);
      return;
    }
    setDocuments((prev) => [result.data, ...prev]);
    formRef.current?.reset();
  }

  async function handleDelete(documentId: string) {
    setDeletingId(documentId);
    setError(null);
    const result = await deleteDocumentAction(workspaceId, documentId);
    setDeletingId(null);

    if (!result.ok) {
      setError(result.message);
      return;
    }
    setDocuments((prev) => prev.filter((document) => document.id !== documentId));
  }

  return (
    <div className="flex flex-col gap-3 border-t pt-3">
      <h4 className="text-sm font-medium">Documents</h4>
      {error && <p className="text-sm text-destructive">{error}</p>}

      <form ref={formRef} onSubmit={handleUpload} className="flex flex-wrap items-center gap-2">
        <input
          type="file"
          name="file"
          accept=".pdf,.txt,application/pdf,text/plain"
          required
          className="text-sm"
        />
        <Button type="submit" size="sm" disabled={uploading}>
          {uploading ? "Uploading..." : "Upload"}
        </Button>
      </form>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading documents...</p>
      ) : documents.length === 0 ? (
        <p className="text-sm text-muted-foreground">No documents uploaded yet.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {documents.map((document) => (
            <li
              key={document.id}
              className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm"
            >
              <div className="min-w-0">
                <p className="truncate font-medium">{document.filename}</p>
                <p className="text-xs text-muted-foreground">
                  {formatSize(document.size_bytes)} &middot;{" "}
                  {new Date(document.created_at).toLocaleString()}
                </p>
              </div>
              <Button
                type="button"
                variant="destructive"
                size="sm"
                disabled={deletingId === document.id}
                onClick={() => handleDelete(document.id)}
              >
                {deletingId === document.id ? "Deleting..." : "Delete"}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
