import { type NextRequest, NextResponse } from "next/server";

import { ApiError, api } from "@/lib/api";
import {
  ACCESS_COOKIE,
  clearSessionCookies,
  isSecureRequest,
  REFRESH_COOKIE,
  setSessionCookies,
} from "@/lib/session";

const PROTECTED = ["/dashboard", "/data"];
const GUEST_ONLY = ["/login", "/register"];

const matches = (path: string, prefixes: string[]) =>
  prefixes.some((prefix) => path === prefix || path.startsWith(`${prefix}/`));

/**
 * Keeps the session alive and gates routes before anything renders.
 * Cookies can only be written here, in server actions and in route handlers, so the
 * access token is refreshed here: Server Components may then assume it is present.
 */
export async function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const refreshed = await refreshSession(request);
  const signedIn = request.cookies.has(ACCESS_COOKIE);

  let response: NextResponse;
  if (!signedIn && matches(pathname, PROTECTED)) {
    const login = new URL("/login", request.url);
    login.searchParams.set("next", `${pathname}${search}`);
    response = NextResponse.redirect(login);
  } else if (signedIn && matches(pathname, GUEST_ONLY)) {
    response = NextResponse.redirect(new URL("/dashboard", request.url));
  } else {
    // Forward the (possibly refreshed) cookies to this very request's render.
    response = NextResponse.next({ request: { headers: request.headers } });
  }

  if (refreshed === "expired") clearSessionCookies(response.cookies);
  else if (refreshed)
    setSessionCookies(response.cookies, refreshed, isSecureRequest(request.headers));
  return response;
}

/** Trades the refresh cookie for a new token pair when the access cookie has expired. */
async function refreshSession(request: NextRequest) {
  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;
  if (request.cookies.has(ACCESS_COOKIE) || !refreshToken) return null;

  try {
    const { token } = await api.refresh(refreshToken);
    request.cookies.set(ACCESS_COOKIE, token.access);
    request.cookies.set(REFRESH_COOKIE, token.refresh);
    return token;
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      request.cookies.delete(REFRESH_COOKIE);
      return "expired" as const;
    }
    // API unreachable: carry on signed out for this request and retry on the next one.
    return null;
  }
}

export const config = {
  matcher: [
    {
      source: "/((?!_next/static|_next/image|favicon.ico|icon.svg|healthz).*)",
      // Prefetches would rotate the refresh token in the background; skip them.
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};
