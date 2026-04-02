"use client";
import useSWR from "swr";
import { fetcher } from "@/lib/api";

type HarvestResponse = {
  days_to_harvest: number;
  projected_date: string;
};

export default function HarvestETA() {
  const { data, isLoading, error } = useSWR<HarvestResponse>("/harvest-eta", fetcher, {
    refreshInterval: 60000,
  });

  if (isLoading) return <div className="card">Calculating…</div>;
  if (error || !data) return <div className="card text-red-600">Harvest ETA unavailable</div>;

  const date = new Date(data.projected_date).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });

  return (
    <div className="card">
      <p className="label">Estimated harvest</p>
      <div className="flex items-end gap-3">
        <p className="text-4xl font-semibold text-[color:var(--brand-secondary)]">{data.days_to_harvest}</p>
        <span className="text-sm text-slate-600">days</span>
      </div>
      <p className="text-sm text-slate-500">Projected date: {date}</p>
    </div>
  );
}
