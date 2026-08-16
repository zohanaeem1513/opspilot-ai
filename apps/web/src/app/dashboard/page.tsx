import { redirect } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { LogoutButton } from "@/components/auth/logout-button";
import { WorkspaceManager } from "@/components/workspaces/workspace-manager";
import { getMe, listWorkspaces } from "@/lib/api";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const {
    data: { session },
  } = await supabase.auth.getSession();

  const me = session ? await getMe(session.access_token) : { ok: false as const };
  const workspacesResult = session
    ? await listWorkspaces(session.access_token)
    : { ok: false as const, status: 0, message: "Your session has expired." };

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-4 py-12 sm:px-6">
      <header className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Signed in as {user.email}</p>
        </div>
        <LogoutButton />
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between gap-2">
            Backend identity check
            {me.ok ? (
              <Badge>Verified</Badge>
            ) : (
              <Badge variant="destructive">Unavailable</Badge>
            )}
          </CardTitle>
          <CardDescription>
            Confirms the FastAPI backend independently verified this
            session&apos;s access token via <code>GET /me</code>.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {me.ok ? (
            <p className="text-sm">
              Backend-confirmed profile id: <span className="font-mono">{me.data.id}</span>
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">
              Could not reach the backend, or it rejected this session&apos;s token.
            </p>
          )}
        </CardContent>
      </Card>

      <WorkspaceManager
        initialWorkspaces={workspacesResult.ok ? workspacesResult.data : []}
        initialError={workspacesResult.ok ? null : workspacesResult.message}
      />
    </div>
  );
}
