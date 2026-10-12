import type { Metadata } from "next";
import Link from "next/link";

import { RegisterForm } from "@/components/register-form";
import { Card } from "@/components/ui";

export const metadata: Metadata = { title: "Create account" };

export default function RegisterPage() {
  return (
    <Card>
      <h1 className="mb-6 text-xl font-semibold">Create an account</h1>
      <RegisterForm />
      <p className="mt-6 text-center text-sm text-zinc-500 dark:text-zinc-400">
        Already registered?{" "}
        <Link href="/login" className="font-medium text-zinc-900 underline dark:text-zinc-100">
          Sign in
        </Link>
      </p>
    </Card>
  );
}
