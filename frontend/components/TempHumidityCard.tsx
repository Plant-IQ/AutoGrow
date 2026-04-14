"use client";
import useSWR from "swr";
import { fetcher } from "@/lib/api";

type ActivePlant = { id: number };
type HistoryPoint = {
  ts: string;
  temp: number;
  humidity: number;
};
type HistoryResponse = {
  points: HistoryPoint[];
};

export default function TempHumidityCard() {
  const { data: activePlant, isLoading: loadingActive } = useSWR<ActivePlant | null>("/plants/active", fetcher);
  const { data, isLoading, error } = useSWR<HistoryResponse>("/history", fetcher, {
    refreshInterval: 30000,
  });

  if (loadingActive || isLoading) return <div className="card">Loading climate sensors…</div>;
  if (!activePlant) return <div className="card">Temperature and humidity appear after a plant starts.</div>;
  if (error || !data) return <div className="card text-red-600">Climate data unavailable</div>;

  const latest = data.points[data.points.length - 1];
  const tempLabel = latest?.temp !== undefined ? `${latest.temp.toFixed(1)}°C` : "N/A";
  const humidityLabel = latest?.humidity !== undefined ? `${latest.humidity.toFixed(0)}% RH` : "N/A";

  return (
    <div className="card space-y-2">
      <p className="label">Temp & Humidity</p>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="rounded-lg bg-slate-50 px-3 py-2">
          <p className="text-xs uppercase tracking-wide text-slate-500">Temperature</p>
          <p className="text-xl font-semibold text-slate-900">{tempLabel}</p>
        </div>
        <div className="rounded-lg bg-slate-50 px-3 py-2">
          <p className="text-xs uppercase tracking-wide text-slate-500">Humidity</p>
          <p className="text-xl font-semibold text-slate-900">{humidityLabel}</p>
        </div>
      </div>
      <p className="text-xs text-slate-500">Collected via KY-015 (DHT11 x2 avg) + MQTT /autogrow/sensors</p>
    </div>
  );
}
