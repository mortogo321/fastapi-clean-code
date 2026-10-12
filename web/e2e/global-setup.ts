import type { FullConfig } from "@playwright/test";

import { API_URL } from "./fixtures";

/** Fails fast, with a hint, when the stack under test is not running. */
export default async function globalSetup(config: FullConfig) {
  const webURL = config.projects[0].use.baseURL ?? "http://localhost:3000";
  for (const url of [new URL("/healthz", webURL), new URL("/api/v1/", API_URL)]) {
    const ok = await fetch(url).then(
      (response) => response.ok,
      () => false,
    );
    if (!ok) {
      throw new Error(
        `${url} is not reachable. Start the stack first: ENV=development docker compose up --build -d`,
      );
    }
  }
}
