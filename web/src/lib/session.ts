/**
 * Session cookies shared by the proxy, the server actions and the route handlers.
 * The browser only ever holds the API tokens as httpOnly cookies.
 */

export const ACCESS_COOKIE = "access_token";
export const REFRESH_COOKIE = "refresh_token";

// Expire the cookie a little before the JWT so a request never carries a token that
// lapses on its way to the API; a missing access cookie triggers a refresh instead.
const EXPIRY_MARGIN_SECONDS = 10;

export type TokenPair = { access: string; refresh: string };

type CookieOptions = {
  httpOnly: boolean;
  secure: boolean;
  sameSite: "lax";
  path: string;
  maxAge?: number;
};

/** The subset of the request/response cookie stores that this module writes to. */
type CookieJar = {
  set(name: string, value: string, options?: CookieOptions): unknown;
  delete(name: string): unknown;
};

/** Seconds until the token's `exp`; the signature is the API's business, not ours. */
function secondsToExpiry(token: string): number | undefined {
  try {
    const payload = JSON.parse(Buffer.from(token.split(".")[1], "base64url").toString());
    if (typeof payload.exp !== "number") return undefined;
    return Math.max(0, payload.exp - Math.floor(Date.now() / 1000) - EXPIRY_MARGIN_SECONDS);
  } catch {
    return undefined;
  }
}

export function setSessionCookies(jar: CookieJar, tokens: TokenPair, secure: boolean) {
  const options = { httpOnly: true, secure, sameSite: "lax", path: "/" } as const;
  jar.set(ACCESS_COOKIE, tokens.access, { ...options, maxAge: secondsToExpiry(tokens.access) });
  jar.set(REFRESH_COOKIE, tokens.refresh, { ...options, maxAge: secondsToExpiry(tokens.refresh) });
}

export function clearSessionCookies(jar: CookieJar) {
  jar.delete(ACCESS_COOKIE);
  jar.delete(REFRESH_COOKIE);
}

/** TLS usually ends at a reverse proxy, so trust its forwarded protocol. */
export function isSecureRequest(headers: { get(name: string): string | null }): boolean {
  return headers.get("x-forwarded-proto")?.split(",")[0].trim() === "https";
}

/** Only same-origin paths are accepted as post-login destinations (no open redirect). */
export function safeNextPath(value: unknown, fallback = "/dashboard"): string {
  if (typeof value !== "string" || !value.startsWith("/")) return fallback;
  const base = "http://localhost";
  try {
    const url = new URL(value, base);
    return url.origin === base ? `${url.pathname}${url.search}` : fallback;
  } catch {
    return fallback;
  }
}
