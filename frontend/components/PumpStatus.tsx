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
type HistoryPoint = {
  ts: string;
  soil: number;
};
type HistoryResponse = {
  points: HistoryPoint[];
};

export default function PumpStatus() {
  const { data: activePlant, isLoading: loadingActive } = useSWR<ActivePlant | null>("/plants/active", fetcher);
  const { data, isLoading, error } = useSWR<PumpResponse>("/pump-status", fetcher, {
    refreshInterval: 30000,
  });
  const { data: history, isLoading: loadingHistory } = useSWR<HistoryResponse>("/history", fetcher, {
    refreshInterval: 30000,
  });

  if (loadingActive || isLoading || loadingHistory) return <div className="card">Loading irrigation telemetry…</div>;
  if (!activePlant) return <div className="card">Irrigation and root-zone data appears after a plant starts.</div>;
  if (error || !data) return <div className="card text-red-600">Irrigation telemetry unavailable</div>;

  const last = new Date(data.last_checked).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const latestSoil = history?.points?.[history.points.length - 1]?.soil;
  const soilLabel = latestSoil !== undefined ? `${latestSoil.toFixed(1)}%` : "N/A";
  const soilPct = latestSoil !== undefined ? Math.max(0, Math.min(100, latestSoil)) : 0;
  const pumpStatusLabel = data.ok ? "Pump active" : "Pump idle";
  const pumpStatusTone = data.ok
    ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
    : "bg-slate-100 text-slate-700 border border-slate-200";

  return (
    <div className="card relative overflow-hidden flex flex-col h-full gap-3" style={{ minHeight: 130 }}>

      <div className="flex items-center justify-between">
        <p className="label">Irrigation Monitor</p>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${pumpStatusTone}`}>{pumpStatusLabel}</span>
      </div>

      <div className="grid gap-2">
        <div className="rounded-xl border border-slate-200 bg-white/55 px-3 py-2">
          <p className="text-xs uppercase tracking-wide text-slate-500">Pump vibration</p>
          <p className="text-3xl font-semibold text-slate-900 leading-tight">{data.vibration.toFixed(2)}</p>
          <p className="mt-1 text-xs text-slate-500">Sensor KY-002 · MQTT /autogrow/sensors</p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white/55 px-3 py-2">
          <div className="flex items-end justify-between">
            <p className="text-xs uppercase tracking-wide text-slate-500">Soil moisture</p>
            <p className="text-2xl font-semibold text-slate-900 leading-tight">{soilLabel}</p>
          </div>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-200">
            <div className="h-full rounded-full bg-emerald-500" style={{ width: `${soilPct}%` }} />
          </div>
          <p className="mt-1 text-xs text-slate-500">Sensor ZX-SOIL (ADC) · MQTT /autogrow/sensors</p>
        </div>
      </div>

      <div className="mt-auto">
        <p className="text-xs text-slate-500">Last checked {last}</p>
      </div>
    </div>
  );
}
