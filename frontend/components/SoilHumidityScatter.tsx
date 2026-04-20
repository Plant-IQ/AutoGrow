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

import { DEFAULT_LAT, DEFAULT_LON, realFetcher } from "@/lib/api";

const DRY_SOIL_THRESHOLD = 40;
const MATCH_WINDOW_MS = 90 * 60 * 1000;
const HISTORY_PATH = "/history?until_stage=Veg";

type RawReading = Record<string, unknown>;

type NormalizedReading = {
  ts: string;
  value: number;
};

type ScatterPoint = {
  outdoorHumidity: number;
  soilMoisture: number;
  soilTimestamp: string;
  outdoorTimestamp?: string;
  matchedTimestamp?: string;
  isDry: boolean;
};

type HistoryResponse = {
  points?: RawReading[];
};

type OutdoorHistoryResponse = {
  points?: RawReading[];
  fetched_at?: string;
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

function matchNearestPoints(soilSeries: NormalizedReading[], outdoorSeries: NormalizedReading[]): ScatterPoint[] {
  if (soilSeries.length === 0 || outdoorSeries.length === 0) return [];

  let outdoorIndex = 0;

  return soilSeries
    .map((soilPoint): ScatterPoint | null => {
      while (
        outdoorIndex < outdoorSeries.length - 1 &&
        Math.abs(Date.parse(outdoorSeries[outdoorIndex + 1].ts) - Date.parse(soilPoint.ts)) <=
          Math.abs(Date.parse(outdoorSeries[outdoorIndex].ts) - Date.parse(soilPoint.ts))
      ) {
        outdoorIndex += 1;
      }

      const outdoorPoint = outdoorSeries[outdoorIndex];
      if (!outdoorPoint) return null;

      const timeDelta = Math.abs(Date.parse(outdoorPoint.ts) - Date.parse(soilPoint.ts));
      if (timeDelta > MATCH_WINDOW_MS) return null;

      return {
        outdoorHumidity: round1(outdoorPoint.value),
        soilMoisture: round1(soilPoint.value),
        soilTimestamp: soilPoint.ts,
        outdoorTimestamp: outdoorPoint.ts,
        matchedTimestamp: soilPoint.ts,
        isDry: soilPoint.value < DRY_SOIL_THRESHOLD,
      };
    })
    .filter((point): point is ScatterPoint => point !== null);
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
      <p className="mt-2 font-medium text-slate-900">{formatDateTime(point.matchedTimestamp ?? point.soilTimestamp)}</p>
      <div className="mt-2 space-y-1">
        <p>Outdoor Humidity: {point.outdoorHumidity.toFixed(1)}%</p>
        <p>Soil Moisture: {point.soilMoisture.toFixed(1)}%</p>
      </div>
      <p className="mt-2 text-xs text-slate-500">Soil: {formatDateTime(point.soilTimestamp)}</p>
      {point.outdoorTimestamp ? <p className="text-xs text-slate-500">Outdoor: {formatDateTime(point.outdoorTimestamp)}</p> : null}
    </div>
  );
}

export default function SoilHumidityScatter() {
  const {
    data: historyData,
    isLoading: soilLoading,
    error: soilError,
  } = useSWR<HistoryResponse>(HISTORY_PATH, realFetcher, { refreshInterval: 60_000 });
  const {
    data: outdoorData,
    isLoading: outdoorLoading,
    error: outdoorError,
  } = useSWR<OutdoorHistoryResponse>(`/outdoor/history?lat=${DEFAULT_LAT}&lon=${DEFAULT_LON}&past_days=7`, realFetcher, {
    refreshInterval: 5 * 60_000,
  });

  if (soilLoading || outdoorLoading) return <div className="card">Loading soil and outdoor correlation…</div>;
  if (soilError || outdoorError) return <div className="card text-red-600">Correlation chart unavailable</div>;

  const soilSeries = normalizeSeries(historyData, "soil");
  const outdoorSeries = normalizeSeries(outdoorData, "humidity");
  const chartData = matchNearestPoints(soilSeries, outdoorSeries);

  if (soilSeries.length === 0 || outdoorSeries.length === 0) {
    return <div className="card">Soil or outdoor humidity history is not available yet.</div>;
  }

  if (chartData.length === 0) {
    return <div className="card">No nearby soil and outdoor humidity readings could be matched yet.</div>;
  }

  return (
    <div className="card">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="label">Soil vs outdoor humidity</p>
          <h2 className="text-lg font-semibold text-slate-900">Moisture correlation scatter</h2>
        </div>
        <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500">
          Dry soil threshold: below {DRY_SOIL_THRESHOLD}%
        </div>
      </div>

      <div className="rounded-2xl border border-[#e2e8f0] bg-[linear-gradient(180deg,#ffffff_0%,#f8fbfd_100%)] p-3">
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 16, right: 20, bottom: 16, left: 4 }}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis
                type="number"
                dataKey="outdoorHumidity"
                name="Outdoor Humidity"
                unit="%"
                domain={[0, 100]}
                stroke="#94a3b8"
                tick={{ fontSize: 12, fill: "#94a3b8" }}
                label={{ value: "Outdoor Humidity (%)", position: "insideBottom", offset: -6, fill: "#94a3b8" }}
              />
              <YAxis
                type="number"
                dataKey="soilMoisture"
                name="Soil Moisture"
                unit="%"
                domain={[0, 100]}
                stroke="#94a3b8"
                tick={{ fontSize: 12, fill: "#94a3b8" }}
                label={{
                  value: "Soil Moisture (%)",
                  angle: -90,
                  position: "insideLeft",
                  offset: 10,
                  style: { 
                    textAnchor: "middle",
                    fill: "#94a3b8",
                    fontSize: 14 
                  }
                }}
              />
              <ReferenceLine
                y={DRY_SOIL_THRESHOLD}
                stroke="#c46d43"
                strokeDasharray="6 4"
                ifOverflow="extendDomain"
                label={{ value: "Dry soil", fill: "#a15833", fontSize: 12, position: "insideTopLeft" }}
              />
              <Tooltip cursor={{ strokeDasharray: "3 3", stroke: "#94a3b8" }} content={<ScatterTooltip />} />
              <Scatter data={chartData} shape="circle">
                {chartData.map((point, index) => (
                  <Cell
                    key={`${point.soilTimestamp}-${point.outdoorTimestamp}-${index}`}
                    fill={point.isDry ? "#c46d43" : "#7ba97c"}
                    stroke={point.isDry ? "#9c4f29" : "#597d5a"}
                    strokeWidth={1.5}
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>

      <p className="text-xs text-slate-500">
        Using real backend endpoints: soil moisture from `/history` and outdoor humidity history from `/outdoor/history`.
      </p>
    </div>
  );
}
