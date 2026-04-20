"use client";

import useSWR from "swr";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { DEFAULT_LAT, DEFAULT_LON, realFetcher } from "@/lib/api";
const HISTORY_PATH = "/history?until_stage=Veg";

type HistoryPoint = {
  ts: string;
  temp: number;
  humidity: number;
};

type HistoryResponse = {
  points?: HistoryPoint[];
};

type OutdoorDailyPoint = {
  date: string;
  avg_temp: number;
};

type OutdoorDailyResponse = {
  points?: OutdoorDailyPoint[];
};

type ChartRow = {
  dateKey: string;
  dateLabel: string;
  glasshouseTemp: number;
  outdoorTemp?: number;
  glasshouseHumidity: number;
};

function formatDateLabel(date: string) {
  return new Date(date).toLocaleDateString([], {
    month: "short",
    day: "numeric",
  });
}

function buildDailyAverages(points: HistoryPoint[]): ChartRow[] {
  const grouped = new Map<string, { tempSum: number; humiditySum: number; count: number }>();

  for (const point of points) {
    const dateKey = new Date(point.ts).toISOString().slice(0, 10);
    const bucket = grouped.get(dateKey) ?? { tempSum: 0, humiditySum: 0, count: 0 };
    bucket.tempSum += point.temp;
    bucket.humiditySum += point.humidity;
    bucket.count += 1;
    grouped.set(dateKey, bucket);
  }

  return Array.from(grouped.entries())
    .map(([dateKey, bucket]) => ({
      dateKey,
      dateLabel: formatDateLabel(dateKey),
      glasshouseTemp: bucket.tempSum / bucket.count,
      glasshouseHumidity: bucket.humiditySum / bucket.count,
    }))
    .slice(-7);
}

function mergeOutdoorTemps(rows: ChartRow[], outdoorPoints: OutdoorDailyPoint[]): ChartRow[] {
  const outdoorMap = new Map(
    outdoorPoints.map((point) => [new Date(point.date).toISOString().slice(0, 10), point.avg_temp])
  );

  return rows.map((row) => ({
    ...row,
    outdoorTemp: outdoorMap.get(row.dateKey),
  }));
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value?: number; name?: string; color?: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-xl border border-[#e2e8f0] bg-white px-4 py-3 text-sm text-slate-800 shadow-lg">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">{label}</p>
      <div className="mt-2 space-y-1">
        {payload.map((item) => {
          const unit = item.name?.includes("Humidity") ? "%" : "°C";
          return (
            <p key={item.name} style={{ color: item.color ?? "#334155" }}>
              {item.name}: {item.value?.toFixed(1)}
              {unit}
            </p>
          );
        })}
      </div>
    </div>
  );
}

export default function DailyTempHumidityComparisonBarChart() {
  const {
    data: historyData,
    isLoading: glasshouseLoading,
    error: glasshouseError,
  } = useSWR<HistoryResponse>(HISTORY_PATH, realFetcher, {
    refreshInterval: 60_000,
  });
  const {
    data: outdoorData,
    isLoading: outdoorLoading,
    error: outdoorError,
  } = useSWR<OutdoorDailyResponse>(`/outdoor/daily-avg?lat=${DEFAULT_LAT}&lon=${DEFAULT_LON}&past_days=7`, realFetcher, {
    refreshInterval: 5 * 60_000,
  });

  if (glasshouseLoading || outdoorLoading) return <div className="card">Loading daily comparisons…</div>;
  if (glasshouseError || outdoorError) return <div className="card text-red-600">Daily comparison unavailable</div>;

  const dailyRows = buildDailyAverages(historyData?.points ?? []);
  const chartData = mergeOutdoorTemps(dailyRows, outdoorData?.points ?? []);

  if (chartData.length === 0) {
    return <div className="card">Daily glasshouse averages are not available yet.</div>;
  }

  return (
    <div className="card">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="label">Daily comparison</p>
          <h2 className="text-lg font-semibold text-slate-900">Glasshouse vs outdoor daily averages</h2>
        </div>
        <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500">Last 7 days</div>
      </div>

      <div className="rounded-2xl border border-[#e2e8f0] bg-[linear-gradient(180deg,#ffffff_0%,#f8fbfd_100%)] p-3 mt-4">
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            {/* ปรับ margin ขอบซ้ายและขวา เพื่อให้มีที่ว่างสำหรับ Label แกน Y */}
            <BarChart data={chartData} margin={{ top: 16, right: 20, bottom: 16, left: 16 }} barGap={8}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis dataKey="dateLabel" stroke="#94a3b8" tick={{ fontSize: 12, fill: "#94a3b8" }} />
              <YAxis
                yAxisId="left"
                stroke="#94a3b8"
                tick={{ fontSize: 12, fill: "#94a3b8" }}
                label={{ 
                  value: "Temp (°C)", 
                  angle: -90, 
                  position: "insideLeft", 
                  fill: "#94a3b8",
                  style: { textAnchor: "middle" } // จัดกึ่งกลาง
                }}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                stroke="#94a3b8"
                tick={{ fontSize: 12, fill: "#94a3b8" }}
                label={{ 
                  value: "Humidity (%)", 
                  angle: 90, 
                  position: "insideRight", 
                  fill: "#94a3b8",
                  style: { textAnchor: "middle" } // จัดกึ่งกลาง
                }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12, color: "#94a3b8" }} />
              <Bar yAxisId="left" dataKey="glasshouseTemp" name="Glasshouse Temp" fill="#6fb2d2" radius={[6, 6, 0, 0]} />
              <Bar yAxisId="left" dataKey="outdoorTemp" name="Outdoor Temp" fill="#d78451" radius={[6, 6, 0, 0]} />
              <Bar
                yAxisId="right"
                dataKey="glasshouseHumidity"
                name="Glasshouse Humidity"
                fill="#85c78a"
                radius={[6, 6, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <p className="mt-2 text-xs text-slate-500">
        Using real backend endpoints: daily glasshouse averages are derived from `/history`; outdoor daily averages come from `/outdoor/daily-avg`.
      </p>
    </div>
  );
}