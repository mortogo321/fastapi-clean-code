import type { ComponentProps, ReactNode } from "react";

/** Small presentational building blocks shared by the pages. */

export function Card({ className = "", ...props }: ComponentProps<"section">) {
  return (
    <section
      className={`rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 ${className}`}
      {...props}
    />
  );
}

export function PageHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <header className="mb-6">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      {children && <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">{children}</p>}
    </header>
  );
}

export function Button({ className = "", ...props }: ComponentProps<"button">) {
  return (
    <button
      className={`inline-flex items-center justify-center rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300 dark:focus-visible:outline-zinc-100 ${className}`}
      {...props}
    />
  );
}

export function Field({
  label,
  error,
  ...input
}: ComponentProps<"input"> & { label: string; name: string; error?: string }) {
  const errorId = `${input.name}-error`;
  return (
    <label className="block">
      <span className="text-sm font-medium">{label}</span>
      <input
        className="mt-1 block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm shadow-xs outline-none focus:border-zinc-500 focus:ring-2 focus:ring-zinc-200 aria-invalid:border-red-500 dark:border-zinc-700 dark:bg-zinc-950 dark:focus:ring-zinc-800"
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        {...input}
      />
      {error && (
        <span
          id={errorId}
          className="mt-1 block text-sm text-red-600 first-letter:uppercase dark:text-red-400"
        >
          {error}
        </span>
      )}
    </label>
  );
}

export function Alert({ children }: { children: ReactNode }) {
  return (
    <p
      role="alert"
      className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 first-letter:uppercase dark:border-red-900 dark:bg-red-950 dark:text-red-300"
    >
      {children}
    </p>
  );
}
