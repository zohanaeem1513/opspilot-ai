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
