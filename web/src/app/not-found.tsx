import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-[60dvh] flex-col items-center justify-center gap-3 px-4 text-center">
      <p className="font-mono text-sm text-zinc-500">404</p>
      <h1 className="text-xl font-semibold">Not found</h1>
      <p className="text-sm text-zinc-500">
        This page or record does not exist, or it is not yours to see.
      </p>
      <Link href="/" className="mt-2 text-sm font-medium underline">
        Back to the console
      </Link>
    </main>
  );
}
