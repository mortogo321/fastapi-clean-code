import { expect, submitLogin, test } from "./fixtures";

test("sends the security headers", async ({ request }) => {
  const response = await request.get("/login");
  expect(response.status()).toBe(200);

  const headers = response.headers();
  expect(headers["content-security-policy"]).toContain("frame-ancestors 'none'");
  expect(headers).toMatchObject({
    "x-frame-options": "DENY",
    "x-content-type-options": "nosniff",
    "referrer-policy": "strict-origin-when-cross-origin",
  });
  expect(headers["x-powered-by"]).toBeUndefined();
});

// After sign-in, `next` may only point back into the app (no open redirect).
for (const next of ["https://evil.example/", "//evil.example/", "/\\evil.example/"]) {
  test(`ignores the off-site redirect target ${next}`, async ({ page, account }) => {
    await page.goto(`/login?next=${encodeURIComponent(next)}`);
    await submitLogin(page, account);
    await expect(page).toHaveURL("/dashboard");
  });
}
