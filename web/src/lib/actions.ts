"use server";

import type { Route } from "next";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";

import { ApiError, api } from "./api";
import {
  clearSessionCookies,
  isSecureRequest,
  REFRESH_COOKIE,
  safeNextPath,
  setSessionCookies,
  type TokenPair,
} from "./session";

export type FormState = {
  error?: string;
  fieldErrors?: Record<string, string>;
  // Echoed back so the form keeps what the user typed (never the password).
  values?: Record<string, string>;
};

const text = (form: FormData, name: string) => String(form.get(name) ?? "");

async function startSession(tokens: TokenPair) {
  setSessionCookies(await cookies(), tokens, isSecureRequest(await headers()));
}

/** Maps an API error onto the form: validation details per field, the rest as a banner. */
function toFormState(error: unknown, values: Record<string, string>): FormState {
  if (!(error instanceof ApiError)) {
    console.error(error);
    return { error: "The service is unavailable. Please try again shortly.", values };
  }
  if (error.details.length > 0) {
    const fieldErrors = Object.fromEntries(error.details.map((d) => [d.field, d.message]));
    return { fieldErrors, values };
  }
  if (error.code === "users-001") return { fieldErrors: { email: error.message }, values };
  return { error: error.message, values };
}

export async function login(_: FormState, form: FormData): Promise<FormState> {
  const values = { email: text(form, "email") };
  try {
    const { token } = await api.login({ ...values, password: text(form, "password") });
    await startSession(token);
  } catch (error) {
    return toFormState(error, values);
  }
  redirect(safeNextPath(form.get("next")) as Route);
}

export async function register(_: FormState, form: FormData): Promise<FormState> {
  const values = {
    email: text(form, "email"),
    first_name: text(form, "first_name"),
    last_name: text(form, "last_name"),
  };
  const password = text(form, "password");
  try {
    await api.register({ ...values, password });
    const { token } = await api.login({ email: values.email, password });
    await startSession(token);
  } catch (error) {
    return toFormState(error, values);
  }
  redirect("/dashboard");
}

export async function logout() {
  const jar = await cookies();
  const refreshToken = jar.get(REFRESH_COOKIE)?.value;
  if (refreshToken) {
    // Best effort: the cookies are dropped either way, and an unknown token is already dead.
    await api.logout(refreshToken).catch(() => undefined);
  }
  clearSessionCookies(jar);
  redirect("/login");
}
