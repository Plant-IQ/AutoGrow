"use client";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import Image from "next/image";

type PumpResponse = {
  ok: boolean;
  vibration: number;
  last_checked: string;
};
type ActivePlant = { id: number };

export default function PumpStatus() {
  const { data: activePlant, isLoading: loadingActive } = useSWR<ActivePlant | null>("/plants/active", fetcher);
  const { data, isLoading, error } = useSWR<PumpResponse>("/pump-status", fetcher, {
    refreshInterval: 30000,
  });

  if (loadingActive || isLoading) return <div className="card">Checking pump…</div>;
  if (!activePlant) return <div className="card">Pump idle until a new plant starts.</div>;
  if (error || !data) return <div className="card text-red-600">Pump status unavailable</div>;

  const last = new Date(data.last_checked).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <div className="card relative overflow-hidden flex flex-col h-full" style={{ minHeight: 130 }}>
      <Image
        src="/assets/icons/water_drop.png"
        alt="Water drop"
        width={64}
        height={64}
        className="absolute right-1.5 top-3 h-14 w-14 object-contain opacity-90 select-none"
        priority
      />

      <div className="flex items-center gap-2 mb-1">
        <p className="label">Pump vibration</p>
        <span
          className={`ml-1 h-2 w-2 rounded-full ${
            data.ok ? "bg-[color:var(--brand-secondary)] shadow-[0_0_0_4px_rgba(133,200,138,0.18)]" : "bg-red-500"
          }`}
        />
      </div>

      <div className="mt-auto flex items-end justify-between gap-4">
        <div>
          <div className="flex items-baseline gap-2">
            <p className="text-sm font-semibold text-slate-700">Vibration</p>
            <p className="text-xl font-semibold text-slate-900">{data.vibration.toFixed(2)}</p>
          </div>
          <p className="text-xs text-slate-500">Last checked {last}</p>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-sm font-semibold ${
            data.ok ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-red-50 text-red-700 border border-red-200"
          }`}
        >
          {data.ok ? "OK" : "Attention needed"}
        </span>
      </div>
    </div>
  );
}
