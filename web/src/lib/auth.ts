import "server-only";

import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";

import { ApiError } from "./api";
import { ACCESS_COOKIE } from "./session";

/**
 * Runs an authenticated API call with the access token from the session cookie.
 * Server Components cannot write cookies, so a rejected token is handed to the
 * /session/expired route handler, which clears them and sends the user to /login.
 */
export async function withSession<T>(call: (token: string) => Promise<T>): Promise<T> {
  const token = (await cookies()).get(ACCESS_COOKIE)?.value;
  if (!token) redirect("/login");

  try {
    return await call(token);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) redirect("/session/expired");
    throw error;
  }
}

/** Turns an API 404 (unknown model or record) into the not-found page. */
export function notFoundOn404(error: unknown): never {
  if (error instanceof ApiError && error.status === 404) notFound();
  throw error;
}
