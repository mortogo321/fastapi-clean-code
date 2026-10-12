import type { Metadata } from "next";
import Link from "next/link";

import { Card, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { notFoundOn404, withSession } from "@/lib/auth";
import { formatValue, humanize } from "@/lib/format";

const PAGE_SIZE = 10;

export async function generateMetadata({ params }: PageProps<"/data/[slug]">): Promise<Metadata> {
  return { title: humanize((await params).slug) };
}

export default async function DataListPage({ params, searchParams }: PageProps<"/data/[slug]">) {
  const { slug } = await params;
  const requested = Number((await searchParams).page);
  const page = Number.isInteger(requested) && requested > 0 ? requested : 1;

  const result = await withSession((token) => api.list(token, slug, page, PAGE_SIZE)).catch(
    notFoundOn404,
  );
  const { fields } = result.data_schema;

  return (
    <>
      <nav className="mb-2 text-sm text-zinc-500">
        <Link href="/data" className="hover:underline">
          Data
        </Link>{" "}
        / {slug}
      </nav>
      <PageHeader title={humanize(slug)}>
        {result.total_data} {result.total_data === 1 ? "record" : "records"}
      </PageHeader>
      <Card className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-zinc-200 bg-zinc-50 text-xs tracking-wide text-zinc-500 uppercase dark:border-zinc-800 dark:bg-zinc-900/60">
              <tr>
                {fields.map((field) => (
                  <th
                    key={field.name}
                    scope="col"
                    className="px-4 py-3 font-medium whitespace-nowrap"
                  >
                    {humanize(field.name)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {result.data.map((row) => (
                <tr key={String(row.id)} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
                  {fields.map((field) => (
                    <td key={field.name} className="max-w-xs truncate px-4 py-3 whitespace-nowrap">
                      {field.name === "id" ? (
                        <Link
                          href={`/data/${slug}/${String(row.id)}`}
                          className="font-medium underline-offset-2 hover:underline"
                        >
                          {String(row.id)}
                        </Link>
                      ) : (
                        formatValue(row[field.name], field.type)
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {result.data.length === 0 && (
          <p className="px-4 py-10 text-center text-sm text-zinc-500">No records on this page.</p>
        )}
      </Card>
      <Pagination slug={slug} page={page} totalPages={result.total_page} />
    </>
  );
}

function Pagination({
  slug,
  page,
  totalPages,
}: {
  slug: string;
  page: number;
  totalPages: number;
}) {
  if (totalPages <= 1) return null;
  const link =
    "rounded-lg border border-zinc-200 px-3 py-1.5 hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800";
  return (
    <nav aria-label="Pagination" className="mt-4 flex items-center justify-between text-sm">
      <span className="text-zinc-500">
        Page {page} of {totalPages}
      </span>
      <div className="flex gap-2">
        {page > 1 && (
          <Link href={`/data/${slug}?page=${page - 1}`} className={link}>
            Previous
          </Link>
        )}
        {page < totalPages && (
          <Link href={`/data/${slug}?page=${page + 1}`} className={link}>
            Next
          </Link>
        )}
      </div>
    </nav>
  );
}
