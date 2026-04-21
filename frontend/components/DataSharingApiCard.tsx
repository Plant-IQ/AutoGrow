"use client";

type ApiRow = {
  method: "GET" | "POST";
  endpoint: string;
  description: string;
};

const apiRows: ApiRow[] = [
  { method: "GET", endpoint: "/plants/active", description: "Get active plant info" },
  { method: "GET", endpoint: "/plants", description: "List current plant sessions" },
  { method: "GET", endpoint: "/stage", description: "Get current growth stage summary" },
  { method: "GET", endpoint: "/harvest-eta", description: "Get projected harvest timing" },
  { method: "GET", endpoint: "/plant-types", description: "Get available plant type templates" },
  { method: "GET", endpoint: "/light", description: "Get current light telemetry" },
  { method: "GET", endpoint: "/pump-status", description: "Get current pump vibration and status" },
  { method: "GET", endpoint: "/health", description: "Get overall health score and components" },
  { method: "GET", endpoint: "/history", description: "Get sensor history timeline" },
  { method: "GET", endpoint: "/context/weather", description: "Get weather context from openweathermap" },
  { method: "POST", endpoint: "/plants/start", description: "Start a new active plant session" },
  { method: "POST", endpoint: "/stage/reset", description: "Reset the plant stage to seed" },
  { method: "POST", endpoint: "/plants/harvest-active", description: "Harvest and clear the active plant" },
  { method: "POST", endpoint: "/light", description: "Update current light telemetry" },
];

function MethodBadge({ method }: { method: ApiRow["method"] }) {
  const className =
    method === "GET"
      ? "bg-[#85c78a]/20 text-[#4b7a4f] border-[#85c78a]/40"
      : "bg-[#6fb2d2]/20 text-[#4a8fb0] border-[#6fb2d2]/40";

  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold tracking-[0.12em] ${className}`}>
      {method}
    </span>
  );
}

export default function DataSharingApiCard() {
  return (
    <div className="card">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="label">Open API</p>
          <h2 className="text-lg font-semibold text-slate-900">Data Sharing API</h2>
        </div>
        <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500">
          No authentication required
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-[#e2e8f0] bg-[linear-gradient(180deg,#ffffff_0%,#f8fbfd_100%)]">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm text-slate-800">
            <thead className="bg-slate-50/80 text-slate-500">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em]">Method</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em]">Endpoint</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em]">Description</th>
              </tr>
            </thead>
            <tbody>
              {apiRows.map((row) => (
                <tr key={`${row.method}-${row.endpoint}`} className="border-t border-[#e2e8f0]">
                  <td className="px-4 py-3 align-top">
                    <MethodBadge method={row.method} />
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-[#94a3b8]">{row.endpoint}</td>
                  <td className="px-4 py-3 text-slate-700">{row.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="space-y-1 text-xs text-slate-500">
        <p>All endpoints return JSON. Base URL: http://localhost:3000</p>
        <p>No authentication required.</p>
      </div>
    </div>
  );
}
