"use client";

import useSWR from "swr";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { realFetcher } from "@/lib/api";
const HISTORY_PATH = "/history?until_stage=Veg";

type RawReading = Record<string, unknown>;

type NormalizedReading = {
  ts: string;
  value: number;
};

type ChartPoint = {
  ts: string;
  timeLabel: string;
  soilMoisture: number;
};

type HistoryResponse = {
  points?: RawReading[];
};

function getReadingRows(payload: unknown): RawReading[] {
  if (Array.isArray(payload)) return payload as RawReading[];
  if (!payload || typeof payload !== "object") return [];

  const container = payload as Record<string, unknown>;
  const candidate = container.points ?? container.data ?? container.readings ?? container.results;
  return Array.isArray(candidate) ? (candidate as RawReading[]) : [];
}

function parseTimestamp(row: RawReading): string | null {
  const value = row.ts ?? row.timestamp ?? row.time ?? row.datetime ?? row.date;
  return typeof value === "string" && !Number.isNaN(Date.parse(value)) ? value : null;
}

function parseValue(row: RawReading, field: string): number | null {
  const candidates = [row.value, row[field], row[field.replace(/_/g, "")]];

  for (const candidate of candidates) {
    if (typeof candidate === "number" && Number.isFinite(candidate)) return candidate;
    if (typeof candidate === "string") {
      const parsed = Number(candidate);
      if (Number.isFinite(parsed)) return parsed;
    }
  }

  return null;
}

function normalizeSeries(payload: unknown, field: string): NormalizedReading[] {
  return getReadingRows(payload)
    .map((row) => {
      const ts = parseTimestamp(row);
      const value = parseValue(row, field);
      if (!ts || value === null) return null;

      return {
        ts,
        value,
      };
    })
    .filter((row): row is NormalizedReading => row !== null)
    .sort((a, b) => Date.parse(a.ts) - Date.parse(b.ts));
}

function formatTime(ts: string) {
  return new Date(ts).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function SoilTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value?: number; payload?: ChartPoint }>;
  label?: string;
}) {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;

  return (
    <div className="rounded-xl border border-[#e2e8f0] bg-white px-4 py-3 text-sm text-slate-800 shadow-lg">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">{label}</p>
      <p className="mt-2 text-slate-900">Soil Moisture: {point.soilMoisture.toFixed(1)}%</p>
    </div>
  );
}

export default function SoilMoisturePumpChart() {
  const {
    data: historyData,
    isLoading: soilLoading,
    error: soilError,
  } = useSWR<HistoryResponse>(HISTORY_PATH, realFetcher, { refreshInterval: 60_000 });

  if (soilLoading) return <div className="card">Loading soil moisture and pump events…</div>;
  if (soilError) return <div className="card text-red-600">Soil moisture chart unavailable</div>;

  const soilSeries = normalizeSeries(historyData, "soil");
  const pumpSeries = getReadingRows(historyData)
    .filter((row) => Boolean(row.pump_on))
    .map((row) => parseTimestamp(row))
    .filter((ts): ts is string => ts !== null);

  if (soilSeries.length === 0) {
    return <div className="card">Soil moisture history is not available yet.</div>;
  }

  const chartData: ChartPoint[] = soilSeries.map((point) => ({
    ts: point.ts,
    timeLabel: formatTime(point.ts),
    soilMoisture: Math.round(point.value * 10) / 10,
  }));

  const pumpReferenceLabels = new Set(pumpSeries.map((ts) => formatTime(ts)));

  return (
    <div className="card">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="label">Soil moisture timeline</p>
          <h2 className="text-lg font-semibold text-slate-900">Soil moisture with pump events</h2>
        </div>
        {/* เปลี่ยนจากข้อความเฉยๆ เป็น สัญลักษณ์เส้นประ + ข้อความ */}
        <div className="flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500">
          <div className="w-5 border-b-2 border-dashed border-[#dc2626]"></div>
          <span>Pump ON</span>
        </div>
      </div>

      <div className="rounded-2xl border border-[#e2e8f0] bg-[linear-gradient(180deg,#ffffff_0%,#f8fbfd_100%)] p-3 mt-4">
        <div className="h-80 w-full">
          {/* เพิ่ม left margin เป็น 16 เพื่อให้มีที่ว่างสำหรับ Label แกน Y ไม่ให้ชิดขอบเกินไป */}
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 16, right: 20, bottom: 16, left: 16 }}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis dataKey="timeLabel" stroke="#94a3b8" tick={{ fontSize: 12, fill: "#94a3b8" }} />
              <YAxis
                domain={[0, 100]}
                stroke="#94a3b8"
                tick={{ fontSize: 12, fill: "#94a3b8" }}
                label={{ 
                  value: "Soil Moisture (%)", 
                  angle: -90, 
                  position: "insideLeft", 
                  fill: "#94a3b8",
                  style: { textAnchor: "middle" } // บังคับให้อยู่กึ่งกลาง
                }}
              />
              <ReferenceLine
                y={40}
                stroke="#6fb2d2"
                strokeDasharray="6 4"
                label={{ value: "Dry threshold", fill: "#4a8fb0", fontSize: 12, position: "insideTopLeft" }}
              />
              {/* ลบ Label "Pump ON" ออกจาก ReferenceLine ตรงนี้ */}
              {Array.from(pumpReferenceLabels).map((timeLabel, index) => (
                <ReferenceLine
                  key={`${timeLabel}-${index}`}
                  x={timeLabel}
                  stroke="#dc2626"
                  strokeDasharray="6 4"
                />
              ))}
              <Tooltip content={<SoilTooltip />} cursor={{ strokeDasharray: "3 3", stroke: "#94a3b8" }} />
              <Area type="monotone" dataKey="soilMoisture" fill="#85c78a" fillOpacity={0.2} stroke="none" />
              <Line type="monotone" dataKey="soilMoisture" stroke="#85c78a" strokeWidth={3} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      <p className="mt-2 text-xs text-slate-500">Using real backend `/history` data for both soil moisture and pump-on markers.</p>
    </div>
  );
}