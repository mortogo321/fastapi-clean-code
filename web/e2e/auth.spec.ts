import {
  expect,
  getCookie,
  newCredentials,
  sessionCookies,
  signIn,
  submitLogin,
  test,
} from "./fixtures";

test.describe("registration", () => {
  test("creates an account and opens the dashboard", async ({ page }) => {
    const user = newCredentials();
    await page.goto("/register");
    await page.getByLabel("First name").fill(user.firstName);
    await page.getByLabel("Last name").fill(user.lastName);
    await page.getByLabel("Email").fill(user.email);
    await page.getByLabel("Password").fill(user.password);
    await page.getByRole("button", { name: "Create account" }).click();

    await expect(page).toHaveURL("/dashboard");
    await expect(page.getByRole("heading", { name: `Welcome, ${user.firstName}` })).toBeVisible();
    await expect(page.getByText(user.email)).toBeVisible();
    await expect(page.getByText("Connected")).toBeVisible();
  });

  test("flags a taken email on its field and keeps what was typed", async ({ page, account }) => {
    await page.goto("/register");
    await page.getByLabel("First name").fill("Grace");
    await page.getByLabel("Last name").fill("Hopper");
    await page.getByLabel("Email").fill(account.email);
    await page.getByLabel("Password").fill("another-password");
    await page.getByRole("button", { name: "Create account" }).click();

    const email = page.getByLabel("Email");
    await expect(email).toHaveAttribute("aria-invalid", "true");
    await expect(email).toHaveAccessibleDescription(/already registered/i);
    await expect(email).toHaveValue(account.email);
    await expect(page.getByLabel("First name")).toHaveValue("Grace");
    await expect(page.getByLabel("Password")).toHaveValue("");
    await expect(page).toHaveURL("/register");
  });

  test("shows the API's validation errors next to each field", async ({ page }) => {
    // Both values pass the browser's own checks but not the API's: the email domain has no dot,
    // and 40 × "é" is within maxlength (characters) but over bcrypt's 72-byte limit.
    await page.goto("/register");
    await page.getByLabel("First name").fill("Ada");
    await page.getByLabel("Last name").fill("Lovelace");
    await page.getByLabel("Email").fill("ada@example");
    await page.getByLabel("Password").fill("é".repeat(40));
    await page.getByRole("button", { name: "Create account" }).click();

    await expect(page.getByLabel("Email")).toHaveAccessibleDescription(/valid email address/i);
    await expect(page.getByLabel("Password")).toHaveAccessibleDescription(/at most 72 bytes/i);
    await expect(page).toHaveURL("/register");
  });
});

test.describe("sign-in", () => {
  test("gives the same answer for a wrong password and an unknown email", async ({
    page,
    account,
  }) => {
    for (const credentials of [
      { email: account.email, password: "wrong-password" },
      { email: `unknown-${account.email}`, password: account.password },
    ]) {
      await page.goto("/login");
      await submitLogin(page, credentials);
      // Scoped to the form: Next.js adds its own role="alert" route announcer to every page.
      await expect(page.locator("form").getByRole("alert")).toHaveText(
        /invalid email or password/i,
      );
      await expect(page.getByLabel("Email")).toHaveValue(credentials.email);
      await expect(page.getByLabel("Password")).toHaveValue("");
    }
  });

  test("returns to the page that asked for a sign-in", async ({ page, account }) => {
    await page.goto("/data/users?page=1");
    await expect(page).toHaveURL("/login?next=%2Fdata%2Fusers%3Fpage%3D1");

    await submitLogin(page, account);
    await expect(page).toHaveURL("/data/users?page=1");
    await expect(page.getByRole("heading", { name: "Users", exact: true })).toBeVisible();
  });

  test("keeps signed-in users out of the guest pages", async ({ page, account }) => {
    await signIn(page, account);
    for (const path of ["/", "/login", "/register"]) {
      await page.goto(path);
      await expect(page).toHaveURL("/dashboard");
    }
  });
});

test("sign-out clears the cookies and revokes the session in the API", async ({
  page,
  context,
  api,
  account,
}) => {
  await signIn(page, account);
  const refresh = (await getCookie(context, "refresh_token")).value;

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL("/login");
  expect(await sessionCookies(context)).toEqual([]);

  await page.goto("/dashboard");
  await expect(page).toHaveURL("/login?next=%2Fdashboard");

  const replay = await api.post("users/refresh-token", { data: { refresh_token: refresh } });
  expect(replay.status()).toBe(401);
});
