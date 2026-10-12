import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ACCESS_COOKIE } from "@/lib/session";

export default async function Home() {
  redirect((await cookies()).has(ACCESS_COOKIE) ? "/dashboard" : "/login");
}
