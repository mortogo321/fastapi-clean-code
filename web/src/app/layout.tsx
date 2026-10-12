import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Clean Code Console", template: "%s · Clean Code Console" },
  description: "A Next.js front end for the clean-architecture FastAPI service.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body className="min-h-dvh">{children}</body>
    </html>
  );
}
