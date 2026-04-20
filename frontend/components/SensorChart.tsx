"use client";
import useSWR from "swr";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  Legend,
} from "recharts";

import { realFetcher } from "@/lib/api";

const HISTORY_PATH = "/history?until_stage=Veg";

type HistoryPoint = {
  ts: string;
  soil: number;
  temp: number;
  humidity: number;
  light: number;
};

type HistoryResponse = {
  points: HistoryPoint[];
};
type ActivePlant = { id: number };

function formatTs(ts: string) {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function SensorChart() {
  const { data: activePlant, isLoading: loadingActive } = useSWR<ActivePlant | null>("/plants/active", realFetcher);
  const { data, isLoading, error } = useSWR<HistoryResponse>(HISTORY_PATH, realFetcher, {
    refreshInterval: 60000,
  });

  if (loadingActive || isLoading) return <div className="card">Loading timeline…</div>;
  if (!activePlant) return <div className="card">No readings yet. Start a plant to begin collecting data.</div>;
  if (error || !data) return <div className="card text-red-600">Timeline unavailable</div>;
  if (data.points.length === 0) return <div className="card">No readings yet for this plant.</div>;

  const chartData = data.points.map((p) => ({
    ...p,
    tsLabel: formatTs(p.ts),
  }));

  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <p className="label">Last readings</p>
        <span className="text-xs text-slate-500">Auto-refreshing</span>
      </div>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 10, bottom: 0, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="tsLabel" tick={{ fontSize: 11 }} stroke="#94a3b8" />
            <YAxis yAxisId="left" stroke="#94a3b8" tick={{ fontSize: 11 }} />
            <YAxis yAxisId="right" orientation="right" stroke="#94a3b8" tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{ borderRadius: 10, borderColor: "#e2e8f0" }}
              labelStyle={{ color: "#0f172a" }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Line yAxisId="left" type="monotone" dataKey="soil" stroke="#85c78a" strokeWidth={2} dot={false} name="Soil %" />
            <Line yAxisId="left" type="monotone" dataKey="humidity" stroke="#6fb2d2" strokeWidth={2} dot={false} name="Humidity %" />
            <Line yAxisId="left" type="monotone" dataKey="temp" stroke="#ebd671" strokeWidth={2} dot={false} name="Temp °C" />
            <Line yAxisId="right" type="monotone" dataKey="light" stroke="#4a8fb0" strokeWidth={2} dot={false} name="Light lux" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
