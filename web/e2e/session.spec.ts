import { expect, getCookie, sessionCookies, signIn, test } from "./fixtures";

test("keeps the tokens in httpOnly, SameSite=Lax cookies", async ({ page, context, account }) => {
  await signIn(page, account);

  const cookies = await sessionCookies(context);
  expect(cookies.map((cookie) => cookie.name).sort()).toEqual(["access_token", "refresh_token"]);
  for (const cookie of cookies) {
    expect(cookie).toMatchObject({ httpOnly: true, sameSite: "Lax", path: "/" });
  }
  expect(await page.evaluate(() => document.cookie)).not.toContain("token");

  // Each cookie lapses with its JWT, so the access cookie goes long before the refresh cookie.
  const access = await getCookie(context, "access_token");
  const refresh = await getCookie(context, "refresh_token");
  expect(access.expires).toBeGreaterThan(Date.now() / 1000);
  expect(access.expires).toBeLessThan(refresh.expires);
});

test("renews an expired access token from the refresh cookie", async ({
  page,
  context,
  api,
  account,
}) => {
  await signIn(page, account);
  const oldRefresh = (await getCookie(context, "refresh_token")).value;

  // Once the access cookie expires, the browser stops sending it.
  await context.clearCookies({ name: "access_token" });
  await page.goto("/data");

  await expect(page.getByRole("heading", { name: "Data", exact: true })).toBeVisible();
  await getCookie(context, "access_token");
  expect((await getCookie(context, "refresh_token")).value).not.toBe(oldRefresh);

  // The pair was rotated: replaying the old refresh token fails.
  const replay = await api.post("users/refresh-token", { data: { refresh_token: oldRefresh } });
  expect(replay.status()).toBe(401);
});

test("sends a session revoked elsewhere back to the login page", async ({
  page,
  context,
  api,
  account,
}) => {
  await signIn(page, account);
  const refresh = (await getCookie(context, "refresh_token")).value;
  const logout = await api.post("users/logout", { data: { refresh_token: refresh } });
  expect(logout.status()).toBe(204);

  // The access cookie is still there, but the API no longer accepts its token.
  await page.goto("/dashboard");
  await expect(page).toHaveURL("/login");
  expect(await sessionCookies(context)).toEqual([]);
});

test("signs the browser out when the refresh token is rejected", async ({
  page,
  context,
  api,
  account,
}) => {
  await signIn(page, account);
  const refresh = (await getCookie(context, "refresh_token")).value;
  await api.post("users/logout", { data: { refresh_token: refresh } });
  await context.clearCookies({ name: "access_token" });

  await page.goto("/dashboard");
  await expect(page).toHaveURL("/login?next=%2Fdashboard");
  expect(await sessionCookies(context)).toEqual([]);
});
