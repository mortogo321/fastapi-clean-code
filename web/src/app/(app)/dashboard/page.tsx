import type { Metadata } from "next";

import { Card, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { withSession } from "@/lib/auth";
import { formatDate } from "@/lib/format";

export const metadata: Metadata = { title: "Dashboard" };

export default async function DashboardPage() {
  const [user, info] = await withSession((token) => Promise.all([api.profile(token), api.info()]));

  const profile = [
    ["Email", user.email],
    ["User ID", String(user.id)],
    ["Member since", formatDate(user.created_at)],
    ["Last updated", formatDate(user.updated_at)],
  ];

  return (
    <>
      <PageHeader title={`Welcome, ${user.first_name}`}>
        Signed in as {user.first_name} {user.last_name}.
      </PageHeader>
      <div className="grid gap-6 md:grid-cols-3">
        <Card className="md:col-span-2">
          <h2 className="mb-4 font-semibold">Profile</h2>
          <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
            {profile.map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs font-medium tracking-wide text-zinc-500 uppercase">
                  {label}
                </dt>
                <dd className="mt-1 text-sm break-all">{value}</dd>
              </div>
            ))}
          </dl>
        </Card>
        <Card>
          <h2 className="mb-4 font-semibold">API</h2>
          <p className="text-sm">{info.name}</p>
          <p className="mt-1 font-mono text-xs text-zinc-500">v{info.version}</p>
          <p className="mt-4 flex items-center gap-2 text-sm text-emerald-700 dark:text-emerald-400">
            <span className="size-2 rounded-full bg-emerald-500" aria-hidden />
            Connected
          </p>
        </Card>
      </div>
    </>
  );
}
