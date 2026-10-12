import type { Metadata } from "next";
import Link from "next/link";

import { LoginForm } from "@/components/login-form";
import { Card } from "@/components/ui";

export const metadata: Metadata = { title: "Sign in" };

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const { next } = await searchParams;
  return (
    <Card>
      <h1 className="mb-6 text-xl font-semibold">Sign in</h1>
      <LoginForm next={typeof next === "string" ? next : undefined} />
      <p className="mt-6 text-center text-sm text-zinc-500 dark:text-zinc-400">
        No account yet?{" "}
        <Link href="/register" className="font-medium text-zinc-900 underline dark:text-zinc-100">
          Create one
        </Link>
      </p>
    </Card>
  );
}
