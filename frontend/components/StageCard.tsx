"use client";
import useSWR from "swr";
import { fetcher } from "@/lib/api";

type StageResponse = {
  stage: number;
  label: string;
  days_in_stage: number;
};

export default function StageCard() {
  const { data, isLoading, error } = useSWR<StageResponse>("/stage", fetcher, {
    refreshInterval: 30000,
  });

  if (isLoading) return <div className="card">Loading stage…</div>;
  if (error) return <div className="card text-red-600">Failed to load stage</div>;

  return (
    <div className="card">
      <p className="label">Current stage</p>
      <div className="flex items-baseline gap-2">
        <p className="text-3xl font-semibold">{data?.label ?? "–"}</p>
            <span className="rounded-full bg-[color:var(--brand-secondary)]/15 px-2 py-1 text-xs font-medium text-[color:var(--brand-secondary)]">
              #{data?.stage}
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-500">Day {data?.days_in_stage}</p>
    </div>
  );
}
