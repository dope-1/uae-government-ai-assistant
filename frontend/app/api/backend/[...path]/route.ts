import type { NextRequest } from "next/server";

const FALLBACK_BACKEND_URL = "http://localhost:8000/api/v1";

function backendBaseUrl(): string {
  return (process.env.BACKEND_INTERNAL_URL ?? FALLBACK_BACKEND_URL).replace(/\/$/, "");
}

async function forward(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  const { path } = await context.params;
  const upstream = new URL(`${backendBaseUrl()}/${path.join("/")}`);
  request.nextUrl.searchParams.forEach((value, key) => upstream.searchParams.append(key, value));

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  const requestId = request.headers.get("x-request-id");
  const forwardedFor = request.headers.get("x-forwarded-for");
  if (contentType) headers.set("content-type", contentType);
  if (requestId) headers.set("x-request-id", requestId);
  if (forwardedFor) headers.set("x-forwarded-for", forwardedFor);

  const method = request.method;
  const body = method === "GET" || method === "HEAD" ? undefined : await request.text();

  try {
    const response = await fetch(upstream, {
      method,
      headers,
      body,
      cache: "no-store",
    });
    const responseHeaders = new Headers();
    const passthroughHeaders = [
      "content-type",
      "x-request-id",
      "x-cache",
      "x-ratelimit-limit",
      "x-ratelimit-remaining",
      "x-ratelimit-reset",
      "retry-after",
    ];
    for (const name of passthroughHeaders) {
      const value = response.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    responseHeaders.set("cache-control", "no-store");
    return new Response(response.body, { status: response.status, headers: responseHeaders });
  } catch {
    return Response.json(
      { detail: "The backend API is currently unavailable." },
      { status: 503 },
    );
  }
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  return forward(request, context);
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  return forward(request, context);
}
