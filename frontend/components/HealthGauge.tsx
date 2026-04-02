"use client";
import useSWR from "swr";
import { fetcher } from "@/lib/api";

type HealthResponse = {
  score: number;
  components: Record<string, number>;
};

export default function HealthGauge() {
  const { data, isLoading, error } = useSWR<HealthResponse>("/health", fetcher, {
    refreshInterval: 60000,
  });

  if (isLoading) return <div className="card">Loading health…</div>;
  if (error || !data) return <div className="card text-red-600">Health unavailable</div>;

  const radius = 48;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(Math.max(data.score / 100, 0), 1);
  const offset = circumference * (1 - progress);

  return (
    <div className="card gap-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="label">Health score</p>
          <p className="text-3xl font-semibold">{data.score}</p>
        </div>
        <svg width={(radius + 8) * 2} height={(radius + 8) * 2}>
          <circle
            cx={radius + 8}
            cy={radius + 8}
            r={radius}
            className="text-slate-200"
            strokeWidth={10}
            stroke="currentColor"
            fill="transparent"
          />
          <circle
            cx={radius + 8}
            cy={radius + 8}
            r={radius}
            strokeWidth={10}
            strokeLinecap="round"
            stroke="url(#healthGradient)"
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            transform={`rotate(-90 ${radius + 8} ${radius + 8})`}
          />
          <defs>
            <linearGradient id="healthGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#85c88a" />
              <stop offset="100%" stopColor="#6fb2d2" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        {Object.entries(data.components).map(([key, val]) => (
          <div key={key} className="rounded-lg bg-slate-50 px-3 py-2">
            <p className="text-xs uppercase tracking-wide text-slate-500">{key}</p>
            <div className="flex items-center gap-2">
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200">
                <div
                  className="h-full rounded-full bg-emerald-500"
                  style={{ width: `${Math.round(val * 100)}%` }}
                />
              </div>
              <span className="text-xs font-medium text-slate-700">{Math.round(val * 100)}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
