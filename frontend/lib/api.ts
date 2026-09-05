import type { Jurisdiction, RAGAnswer, Readiness, ServiceSummary } from "@/lib/types";

const API_ROOT = "/api/backend";

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed with HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Keep the HTTP fallback when the response body is not JSON.
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export async function askAssistant(
  message: string,
  jurisdiction: Jurisdiction | null,
): Promise<RAGAnswer> {
  const response = await fetch(`${API_ROOT}/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ message, jurisdiction }),
  });
  return parseResponse<RAGAnswer>(response);
}

export async function fetchReadiness(): Promise<Readiness> {
  const response = await fetch(`${API_ROOT}/ready`, { cache: "no-store" });
  if (response.status === 503) return (await response.json()) as Readiness;
  return parseResponse<Readiness>(response);
}

export async function fetchServices(
  jurisdiction: Jurisdiction | null,
  query = "",
): Promise<ServiceSummary[]> {
  const params = new URLSearchParams({ limit: "12" });
  if (jurisdiction) params.set("jurisdiction", jurisdiction);
  if (query.trim()) params.set("q", query.trim());
  const response = await fetch(`${API_ROOT}/services?${params}`, { cache: "no-store" });
  return parseResponse<ServiceSummary[]>(response);
}
