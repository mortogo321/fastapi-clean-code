import { apiLogin, expect, newCredentials, register, signIn, test } from "./fixtures";

test("lists the published models and only their public fields", async ({ page, account }) => {
  await signIn(page, account);
  await page.getByRole("link", { name: "Data", exact: true }).click();

  await expect(page).toHaveURL("/data");
  await expect(page.getByRole("link", { name: "Data", exact: true })).toHaveAttribute(
    "aria-current",
    "page",
  );
  await expect(page.getByRole("heading", { level: 2 })).toHaveText([
    "Users",
    "User tokens",
    "User permissions",
  ]);
  await expect(
    page.getByText("id, email, first_name, last_name, created_at, updated_at"),
  ).toBeVisible();
  await expect(page.getByText("id, user_id, expires_at, created_at, updated_at")).toBeVisible();
  await expect(page.getByText(/password|hash/)).toHaveCount(0);
});

test("shows the user's own row and its record page", async ({ page, account }) => {
  await signIn(page, account);
  await page.goto("/data");
  await page.getByRole("heading", { name: "Users", exact: true }).click();

  await expect(page).toHaveURL("/data/users");
  await expect(page.getByText("1 record", { exact: true })).toBeVisible();
  await expect(page.getByRole("columnheader")).toHaveText([
    "Id",
    "Email",
    "First name",
    "Last name",
    "Created at",
    "Updated at",
  ]);
  const rows = page.getByRole("row").filter({ has: page.getByRole("cell") });
  await expect(rows).toHaveCount(1);
  await expect(rows).toContainText(account.email);

  await page.getByRole("link", { name: String(account.id), exact: true }).click();
  await expect(page).toHaveURL(`/data/users/${account.id}`);
  await expect(page.getByRole("heading", { name: `Users #${account.id}` })).toBeVisible();
  await expect(page.getByRole("term")).toHaveText([
    "Id",
    "Email",
    "First name",
    "Last name",
    "Created at",
    "Updated at",
  ]);
  await expect(page.getByRole("definition").nth(1)).toContainText(account.email);

  await page.getByRole("link", { name: "users", exact: true }).click();
  await expect(page).toHaveURL("/data/users");
});

test("pages through the sessions table", async ({ page, api, account }) => {
  // Every login opens a session: 11 here plus the browser's make 12 rows, two pages of 10.
  await Promise.all(Array.from({ length: 11 }, () => apiLogin(api, account)));
  await signIn(page, account);
  await page.goto("/data/user-tokens");

  await expect(page.getByText("12 records", { exact: true })).toBeVisible();
  await expect(page.getByRole("columnheader")).toHaveText([
    "Id",
    "User id",
    "Expires at",
    "Created at",
    "Updated at",
  ]);
  const rows = page.getByRole("row").filter({ has: page.getByRole("cell") });
  const pagination = page.getByRole("navigation", { name: "Pagination" });
  await expect(rows).toHaveCount(10);
  await expect(pagination).toContainText("Page 1 of 2");
  await expect(pagination.getByRole("link", { name: "Previous" })).toHaveCount(0);

  await pagination.getByRole("link", { name: "Next" }).click();
  await expect(page).toHaveURL("/data/user-tokens?page=2");
  await expect(rows).toHaveCount(2);
  await expect(pagination).toContainText("Page 2 of 2");
  await expect(pagination.getByRole("link", { name: "Next" })).toHaveCount(0);

  await pagination.getByRole("link", { name: "Previous" }).click();
  await expect(page).toHaveURL("/data/user-tokens?page=1");
  await expect(rows).toHaveCount(10);
});

test("shows an empty page past the last one", async ({ page, account }) => {
  await signIn(page, account);
  await page.goto("/data/users?page=99");

  await expect(page.getByText("No records on this page.")).toBeVisible();
  await expect(page.getByText("1 record", { exact: true })).toBeVisible();
});

test("answers unknown models and other users' records with a 404", async ({
  page,
  api,
  account,
}) => {
  const other = await register(api, newCredentials());
  await signIn(page, account);

  for (const path of [
    "/data/no-such-model",
    `/data/users/${other.id}`,
    "/data/users/999999999",
    "/data/users/abc",
  ]) {
    const response = await page.goto(path);
    expect(response?.status(), path).toBe(404);
    await expect(page.getByRole("heading", { name: "Not found" })).toBeVisible();
  }
});
