"use client";
import useSWR from "swr";
import { fetcher } from "@/lib/api";

type PumpResponse = {
  ok: boolean;
  vibration: number;
  last_checked: string;
};

export default function PumpStatus() {
  const { data, isLoading, error } = useSWR<PumpResponse>("/pump-status", fetcher, {
    refreshInterval: 30000,
  });

  if (isLoading) return <div className="card">Checking pump…</div>;
  if (error || !data) return <div className="card text-red-600">Pump status unavailable</div>;

  const last = new Date(data.last_checked).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <div className="card">
      <div className="flex items-center gap-2">
        <span
          className={`h-3 w-3 rounded-full ${data.ok ? "bg-[color:var(--brand-secondary)] shadow-[0_0_0_6px_rgba(133,200,138,0.25)]" : "bg-red-500"}`}
        />
        <p className="label">Pump vibration</p>
      </div>
      <p className={`text-xl font-semibold ${data.ok ? "text-emerald-700" : "text-red-600"}`}>
        {data.ok ? "OK" : "Attention"}
      </p>
      <p className="text-sm text-slate-500">Vibration: {data.vibration.toFixed(2)}</p>
      <p className="text-xs text-slate-400">Last checked {last}</p>
    </div>
  );
}
