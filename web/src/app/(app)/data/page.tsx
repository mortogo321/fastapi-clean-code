import type { Metadata } from "next";
import Link from "next/link";

import { Card, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { withSession } from "@/lib/auth";
import { humanize } from "@/lib/format";

export const metadata: Metadata = { title: "Data" };

export default async function DataPage() {
  const schemas = await withSession(async (token) => {
    const { data: slugs } = await api.models(token);
    return Promise.all(slugs.map(async (slug) => ({ slug, ...(await api.describe(token, slug)) })));
  });

  return (
    <>
      <PageHeader title="Data">
        Models published by the API. Unless you are an admin, you only see your own rows.
      </PageHeader>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {schemas.map(({ slug, fields }) => (
          <Link
            key={slug}
            href={`/data/${slug}`}
            className="group rounded-xl focus-visible:outline-2 focus-visible:outline-zinc-500"
          >
            <Card className="h-full transition group-hover:border-zinc-400 dark:group-hover:border-zinc-600">
              <h2 className="font-semibold">{humanize(slug)}</h2>
              <p className="mt-1 font-mono text-xs text-zinc-500">/data/{slug}</p>
              <p className="mt-4 text-sm text-zinc-600 dark:text-zinc-400">
                {fields.map((field) => field.name).join(", ")}
              </p>
            </Card>
          </Link>
        ))}
      </div>
    </>
  );
}
