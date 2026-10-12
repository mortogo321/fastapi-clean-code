import type { Metadata } from "next";
import Link from "next/link";

import { Card, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { notFoundOn404, withSession } from "@/lib/auth";
import { formatValue, humanize } from "@/lib/format";

export async function generateMetadata({
  params,
}: PageProps<"/data/[slug]/[id]">): Promise<Metadata> {
  const { slug, id } = await params;
  return { title: `${humanize(slug)} #${id}` };
}

export default async function RecordPage({ params }: PageProps<"/data/[slug]/[id]">) {
  const { slug, id } = await params;
  const { data, data_schema } = await withSession((token) => api.record(token, slug, id)).catch(
    notFoundOn404,
  );

  return (
    <>
      <nav className="mb-2 text-sm text-zinc-500">
        <Link href="/data" className="hover:underline">
          Data
        </Link>{" "}
        /{" "}
        <Link href={`/data/${slug}`} className="hover:underline">
          {slug}
        </Link>{" "}
        / {id}
      </nav>
      <PageHeader title={`${humanize(slug)} #${id}`} />
      <Card>
        <dl className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {data_schema.fields.map((field) => (
            <div key={field.name} className="grid gap-1 py-3 first:pt-0 last:pb-0 sm:grid-cols-3">
              <dt className="text-sm font-medium text-zinc-500">{humanize(field.name)}</dt>
              <dd className="text-sm break-all sm:col-span-2">
                {formatValue(data[field.name], field.type)}
                <span className="ml-2 font-mono text-xs text-zinc-400">{field.type}</span>
              </dd>
            </div>
          ))}
        </dl>
      </Card>
    </>
  );
}
