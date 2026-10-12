"use client";

import { Button } from "@/components/ui";

type ErrorProps = { error: Error & { digest?: string }; retry: () => void };

export default function ErrorPage({ error, retry }: ErrorProps) {
  return (
    <main className="flex min-h-[60dvh] flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="text-xl font-semibold">Something went wrong</h1>
      <p className="max-w-md text-sm text-zinc-500">
        The API could not complete the request. It may be starting up or unreachable.
        {error.digest && (
          <span className="mt-2 block font-mono text-xs">Reference: {error.digest}</span>
        )}
      </p>
      <Button onClick={retry}>Try again</Button>
    </main>
  );
}
