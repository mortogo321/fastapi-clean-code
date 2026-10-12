import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { clearSessionCookies } from "@/lib/session";

/** Pages land here when the API rejects their token: only a route handler may clear cookies. */
export async function GET() {
  clearSessionCookies(await cookies());
  redirect("/login");
}
