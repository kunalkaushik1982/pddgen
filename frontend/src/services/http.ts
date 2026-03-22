import { appConfig } from "../config/appConfig";
import { getCookieValue } from "./csrf";

const RAW_API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? appConfig.apiBaseUrlFallback;
export const API_BASE_URL = RAW_API_BASE_URL.replace(/\/+$/, "");
const CSRF_COOKIE_NAME = "pdd_generator_csrf";
const CSRF_HEADER_NAME = "X-CSRF-Token";

export function buildApiUrl(path: string): URL {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const origin =
    typeof window !== "undefined" && window.location?.origin ? window.location.origin : appConfig.apiOriginFallback;

  return new URL(`${API_BASE_URL}${normalizedPath}`, origin);
}

export function buildAuthHeaders(extraHeaders: Record<string, string> = {}): Record<string, string> {
  return { ...extraHeaders };
}

export function buildSecurityHeaders(method: string | undefined, headers: Record<string, string>): Record<string, string> {
  if (!method || ["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase())) {
    return headers;
  }

  const csrfToken = getCookieValue(CSRF_COOKIE_NAME);
  if (!csrfToken) {
    return headers;
  }

  return {
    ...headers,
    [CSRF_HEADER_NAME]: csrfToken,
  };
}

export async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      const payload = (await response.json()) as { detail?: string };
      throw new Error(payload.detail || `Request failed with status ${response.status}`);
    }
    const fallback = await response.text();
    throw new Error(fallback || `Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function fetchJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = buildSecurityHeaders(
    init.method,
    buildAuthHeaders(init.headers ? (init.headers as Record<string, string>) : {}),
  );
  const response = await fetch(`${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`, {
    ...init,
    headers,
    credentials: "include",
  });
  return parseJsonResponse<T>(response);
}

export function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

export function getDownloadFilename(response: Response, fallback: string): string {
  const contentDisposition = response.headers.get("content-disposition") ?? "";
  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }

  const quotedMatch = contentDisposition.match(/filename="([^"]+)"/i);
  if (quotedMatch?.[1]) {
    return quotedMatch[1];
  }

  return fallback;
}
