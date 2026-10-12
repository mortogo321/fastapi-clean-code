import "server-only";

import type { TokenPair } from "./session";

/** Typed client for the FastAPI service. Every call runs on the server. */

export type User = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  created_at: string;
  updated_at: string;
};

export type LoginResponse = { user: User; token: TokenPair };

export type ServiceInfo = { name: string; version: string };

export type FieldType = "long" | "string" | "datetime" | "boolean" | "double" | "unknown";

export type RecordSchema = {
  type: "record";
  name: string;
  fields: { name: string; type: FieldType }[];
};

export type DataRecord = Record<string, unknown>;

export type DataPage = {
  data: DataRecord[];
  page: number;
  page_size: number;
  total_page: number;
  total_data: number;
  data_schema: RecordSchema;
};

export type FieldError = { field: string; message: string };

/** An error response from the API, carrying its `trace_id` code (e.g. `users-002`). */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: FieldError[] = [],
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type RequestOptions = { method?: "GET" | "POST"; body?: unknown; token?: string };

async function request<T>(path: string, { method = "GET", body, token }: RequestOptions = {}) {
  // Read at call time so the URL comes from the runtime environment, not the build.
  const baseUrl = process.env.API_URL ?? "http://localhost:8000";
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${baseUrl}/api/v1${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  if (response.status === 204) return undefined as T;

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      response.status,
      payload?.trace_id ?? "unknown",
      payload?.message ?? response.statusText,
      payload?.details ?? [],
    );
  }
  return payload as T;
}

export const api = {
  info: () => request<ServiceInfo>("/"),

  register: (body: { email: string; password: string; first_name: string; last_name: string }) =>
    request<User>("/users/register", { method: "POST", body }),
  login: (body: { email: string; password: string }) =>
    request<LoginResponse>("/users/login", { method: "POST", body }),
  refresh: (refreshToken: string) =>
    request<LoginResponse>("/users/refresh-token", {
      method: "POST",
      body: { refresh_token: refreshToken },
    }),
  logout: (refreshToken: string) =>
    request<void>("/users/logout", { method: "POST", body: { refresh_token: refreshToken } }),
  profile: (token: string) => request<User>("/users/profile", { token }),

  models: (token: string) => request<{ data: string[] }>("/data/", { token }),
  describe: (token: string, slug: string) =>
    request<RecordSchema>(`/data/${encodeURIComponent(slug)}/describe`, { token }),
  list: (token: string, slug: string, page: number, pageSize: number) =>
    request<DataPage>(`/data/${encodeURIComponent(slug)}/?_page=${page}&_pageSize=${pageSize}`, {
      token,
    }),
  record: (token: string, slug: string, id: string) =>
    request<{ data: DataRecord; data_schema: RecordSchema }>(
      `/data/${encodeURIComponent(slug)}/${encodeURIComponent(id)}`,
      { token },
    ),
};
