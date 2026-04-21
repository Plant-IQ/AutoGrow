"use client";

import useSWR from "swr";
import {
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// แก้ไข 1: เปลี่ยน realFetcher เป็น fetcher (ถ้าใน api.ts ของคุณชื่อ fetcher)
import { DEFAULT_LAT, DEFAULT_LON, fetcher } from "@/lib/api";
const MATCH_WINDOW_MS = 90 * 60 * 1000;
const HISTORY_PATH = "/history?until_stage=Veg";

type RawReading = Record<string, unknown>;

type NormalizedReading = {
  ts: string;
  value: number;
};

type ScatterPoint = {
  outdoorTemp: number;
  glasshouseTemp: number;
  matchedTimestamp?: string;
  glasshouseTimestamp: string;
  outdoorTimestamp?: string;
  hotterThanOutside: boolean;
};

type HistoryResponse = {
  points?: RawReading[];
};

type OutdoorHistoryResponse = {
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
  // ทำให้ฟังก์ชันฉลาดขึ้น ช่วยหาชื่อคีย์อื่นๆ ที่น่าจะเป็นไปได้ด้วย
  const candidates = [
    row.value, 
    row[field], 
    row[`${field}1`],            // กรณีเป็น temp1
    row[`${field}2`],            // กรณีเป็น temp2
    row[`${field}erature_2m`],   // กรณีเป็น temperature_2m (Open-Meteo)
    row[`${field}_c`]            // กรณีเป็น temp_c
  ];

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

function matchNearestPoints(glasshouseSeries: NormalizedReading[], outdoorSeries: NormalizedReading[]): ScatterPoint[] {
  if (glasshouseSeries.length === 0 || outdoorSeries.length === 0) return [];

  let outdoorIndex = 0;

  return glasshouseSeries
    .map((glasshousePoint) => {
      while (
        outdoorIndex < outdoorSeries.length - 1 &&
        Math.abs(Date.parse(outdoorSeries[outdoorIndex + 1].ts) - Date.parse(glasshousePoint.ts)) <=
          Math.abs(Date.parse(outdoorSeries[outdoorIndex].ts) - Date.parse(glasshousePoint.ts))
      ) {
        outdoorIndex += 1;
      }

      const outdoorPoint = outdoorSeries[outdoorIndex];
      if (!outdoorPoint) return null;

      const timeDelta = Math.abs(Date.parse(outdoorPoint.ts) - Date.parse(glasshousePoint.ts));
      if (timeDelta > MATCH_WINDOW_MS) return null;

      return {
        outdoorTemp: round1(outdoorPoint.value),
        glasshouseTemp: round1(glasshousePoint.value),
        matchedTimestamp: glasshousePoint.ts,
        glasshouseTimestamp: glasshousePoint.ts,
        outdoorTimestamp: outdoorPoint.ts,
        hotterThanOutside: glasshousePoint.value > outdoorPoint.value,
      };
    })
    .filter((point) => point !== null) as ScatterPoint[];
}

function round1(value: number) {
  return Math.round(value * 10) / 10;
}

function formatDateTime(ts: string) {
  return new Date(ts).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getTemperatureDomain(points: ScatterPoint[]): [number, number] {
  const values = points.flatMap((point) => [point.outdoorTemp, point.glasshouseTemp]);
  // แก้ไข 2: เอาเลข 0 ออก เพื่อไม่ให้สเกลเพี้ยนไปเริ่มที่ติดลบ
  const min = Math.floor(Math.min(...values) - 2);
  const max = Math.ceil(Math.max(...values) + 2);
  return [min, max];
}

function ScatterTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload?: ScatterPoint }>;
}) {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;

  return (
    <div className="rounded-xl border border-[#e2e8f0] bg-white px-4 py-3 text-sm text-slate-800 shadow-lg">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Matched reading</p>
      <p className="mt-2 font-medium text-slate-900">{formatDateTime(point.matchedTimestamp ?? point.glasshouseTimestamp)}</p>
      <div className="mt-2 space-y-1">
        <p>Outdoor Temp: {point.outdoorTemp.toFixed(1)}°C</p>
        <p>Glasshouse Temp: {point.glasshouseTemp.toFixed(1)}°C</p>
      </div>
      <p className="mt-2 text-xs text-slate-500">Glasshouse: {formatDateTime(point.glasshouseTimestamp)}</p>
      {point.outdoorTimestamp ? <p className="text-xs text-slate-500">Outdoor: {formatDateTime(point.outdoorTimestamp)}</p> : null}
    </div>
  );
}

export default function TemperatureComparisonScatter() {
  const {
    data: historyData,
    isLoading: glasshouseLoading,
    error: glasshouseError,
  } = useSWR<HistoryResponse>(HISTORY_PATH, fetcher, { refreshInterval: 60_000 });
  const {
    data: outdoorData,
    isLoading: outdoorLoading,
    error: outdoorError,
  } = useSWR<OutdoorHistoryResponse>(`/outdoor/history?lat=${DEFAULT_LAT}&lon=${DEFAULT_LON}&past_days=7`, fetcher, {
    refreshInterval: 60 * 60 * 1000,
  });

  if (glasshouseLoading || outdoorLoading) return <div className="card">Loading temperature correlation…</div>;
  if (glasshouseError || outdoorError) return <div className="card text-red-600">Temperature comparison unavailable</div>;

  // โค้ดจะค้นหาทั้ง temp, temp1, temperature_2m ให้เองจากฟังก์ชัน parseValue ที่แก้ใหม่
  const glasshouseSeries = normalizeSeries(historyData, "temp");
  const outdoorSeries = normalizeSeries(outdoorData, "temp");
  const chartData = matchNearestPoints(glasshouseSeries, outdoorSeries);

  if (glasshouseSeries.length === 0 || outdoorSeries.length === 0) {
    return <div className="card">Glasshouse or outdoor temperature history is not available yet. (ไม่มีข้อมูลอุณหภูมิ)</div>;
  }

  if (chartData.length === 0) {
    return <div className="card">No nearby glasshouse and outdoor temperature readings could be matched yet. (ไม่สามารถจับคู่เวลาได้)</div>;
  }

  const [domainMin, domainMax] = getTemperatureDomain(chartData);

  return (
    <div className="card">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="label">Glasshouse vs outdoor temperature</p>
          <h2 className="text-lg font-semibold text-slate-900">Temperature comparison scatter</h2>
        </div>
        <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500">
          Above the line means glasshouse is hotter than outside
        </div>
      </div>

      <div className="rounded-2xl border border-[#e2e8f0] bg-[linear-gradient(180deg,#ffffff_0%,#f8fbfd_100%)] p-3 mt-4">
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 16, right: 20, bottom: 28, left: 28 }}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis
                type="number"
                dataKey="outdoorTemp"
                name="Outdoor Temp"
                unit="°C"
                domain={[domainMin, domainMax]}
                stroke="#94a3b8"
                tick={{ fontSize: 12, fill: "#94a3b8" }}
                label={{ value: "Outdoor Temp (°C)", position: "insideBottom", offset: -6, fill: "#94a3b8" }}
              />
              <YAxis
                type="number"
                dataKey="glasshouseTemp"
                name="Glasshouse Temp"
                unit="°C"
                domain={[domainMin, domainMax]}
                stroke="#94a3b8"
                tick={{ fontSize: 12, fill: "#94a3b8" }}
                label={{
                  value: "Glasshouse Temp (°C)",
                  angle: -90,
                  position: "left",
                  offset: 4,
                  dy: -70,
                  fill: "#94a3b8",
                }}
              />
              <ReferenceLine
                segment={[
                  { x: domainMin, y: domainMin },
                  { x: domainMax, y: domainMax },
                ]}
                stroke="#c46d43"
                strokeDasharray="6 4"
                label={{ value: "Indoor = Outdoor", fill: "#a15833", fontSize: 12, position: "insideTopLeft" }}
              />
              <Tooltip cursor={{ strokeDasharray: "3 3", stroke: "#94a3b8" }} content={<ScatterTooltip />} />
              <Scatter data={chartData} shape="circle">
                {chartData.map((point, index) => (
                  <Cell
                    key={`${point.glasshouseTimestamp}-${point.outdoorTimestamp}-${index}`}
                    fill={point.hotterThanOutside ? "#c46d43" : "#6fb2d2"}
                    stroke={point.hotterThanOutside ? "#9c4f29" : "#4a8fb0"}
                    strokeWidth={1.5}
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>

      <p className="text-xs text-slate-500 mt-4">
        Using real backend endpoints: glasshouse temperature from `/history` and outdoor temperature history from `/outdoor/history`.
      </p>
    </div>
  );
}
