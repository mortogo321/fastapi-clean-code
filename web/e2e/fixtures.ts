import { randomUUID } from "node:crypto";

import {
  type APIRequestContext,
  type BrowserContext,
  test as base,
  expect,
  type Page,
} from "@playwright/test";

export { expect };

/** The FastAPI service, called directly to set up users and sessions. */
export const API_URL = process.env.E2E_API_URL ?? "http://localhost:8000";

export type Credentials = { email: string; password: string; firstName: string; lastName: string };
export type Account = Credentials & { id: number };

/** Unused credentials: each test gets its own user, so runs never collide. */
export function newCredentials(): Credentials {
  return {
    email: `e2e-${randomUUID()}@example.com`,
    password: `pw-${randomUUID()}`,
    firstName: "Ada",
    lastName: "Lovelace",
  };
}

export const test = base.extend<{ api: APIRequestContext; account: Account }>({
  /** Client for `/api/v1/`; paths are relative, e.g. `users/login`. */
  api: async ({ playwright }, use) => {
    const api = await playwright.request.newContext({ baseURL: `${API_URL}/api/v1/` });
    await use(api);
    await api.dispose();
  },
  /** A user registered through the API, not signed in yet. */
  account: async ({ api }, use) => {
    await use(await register(api, newCredentials()));
  },
});

export async function register(api: APIRequestContext, credentials: Credentials): Promise<Account> {
  const response = await api.post("users/register", {
    data: {
      email: credentials.email,
      password: credentials.password,
      first_name: credentials.firstName,
      last_name: credentials.lastName,
    },
  });
  expect(response.status()).toBe(201);
  return { ...credentials, id: (await response.json()).id };
}

/** Opens another session for the user straight through the API, like a second device. */
export async function apiLogin(api: APIRequestContext, credentials: Credentials) {
  const response = await api.post("users/login", {
    data: { email: credentials.email, password: credentials.password },
  });
  expect(response.status()).toBe(200);
}

/** Fills in and submits the login form on the current page. */
export async function submitLogin(page: Page, credentials: { email: string; password: string }) {
  await page.getByLabel("Email").fill(credentials.email);
  await page.getByLabel("Password").fill(credentials.password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

/** Signs in through the login form and waits for the dashboard. */
export async function signIn(page: Page, credentials: Credentials) {
  await page.goto("/login");
  await submitLogin(page, credentials);
  await expect(page).toHaveURL("/dashboard");
}

/** The session cookies are httpOnly: only the browser context can read them, never the page. */
export async function sessionCookies(context: BrowserContext) {
  const names = ["access_token", "refresh_token"];
  return (await context.cookies()).filter((cookie) => names.includes(cookie.name));
}

export async function getCookie(context: BrowserContext, name: string) {
  const cookie = (await context.cookies()).find((candidate) => candidate.name === name);
  if (!cookie) throw new Error(`The browser has no ${name} cookie`);
  return cookie;
}
