import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { HealthResult } from "@/lib/api";

export function ServiceStatus({ health }: { health: HealthResult }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-2">
          Backend service status
          {health.ok ? (
            <Badge>Operational</Badge>
          ) : (
            <Badge variant="destructive">Unavailable</Badge>
          )}
        </CardTitle>
        <CardDescription>
          Live status of the FastAPI backend, checked on every page load.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {health.ok ? (
          <dl className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-muted-foreground">Service</dt>
              <dd className="font-medium">{health.data.service}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Version</dt>
              <dd className="font-medium">{health.data.version}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Environment</dt>
              <dd className="font-medium">{health.data.environment}</dd>
            </div>
          </dl>
        ) : (
          <p className="text-sm text-muted-foreground">
            Could not reach the backend at the configured API URL. Start the
            FastAPI server and reload this page to check again.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
