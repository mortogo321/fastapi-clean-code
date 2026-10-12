export default function AuthLayout({ children }: LayoutProps<"/">) {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-4 py-12">
      <p className="mb-6 text-sm font-semibold tracking-wide text-zinc-500 uppercase">
        Clean Code Console
      </p>
      <div className="w-full max-w-sm">{children}</div>
    </main>
  );
}
