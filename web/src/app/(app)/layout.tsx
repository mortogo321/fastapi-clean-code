import Link from "next/link";

import { NavLink } from "@/components/nav-link";
import { logout } from "@/lib/actions";

// Deliberately no API call here: layouts are reused across navigations and prefetches,
// so each page fetches (and handles an expired session) on its own.
export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
        <div className="mx-auto flex h-14 max-w-5xl items-center gap-2 px-4">
          <Link href="/dashboard" className="mr-4 text-sm font-semibold tracking-tight">
            Clean Code Console
          </Link>
          <nav className="flex gap-1">
            <NavLink href="/dashboard">Dashboard</NavLink>
            <NavLink href="/data">Data</NavLink>
          </nav>
          <form action={logout} className="ml-auto">
            <button
              type="submit"
              className="rounded-md px-3 py-1.5 text-sm font-medium text-zinc-600 transition hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
            >
              Sign out
            </button>
          </form>
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">{children}</main>
    </div>
  );
}
