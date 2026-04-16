"use client";
import Image from "next/image";
import useSWR from "swr";
import { fetcher } from "@/lib/api";

type PlantInstance = {
  id: number;
  label: string;
  plant_type_id: number;
  current_stage_index: number;
  stage_started_at: string;
  pending_confirm: boolean;
};

type PlantLight = {
  plant_id: number;
  stage: number;
  color: string;
  pending_confirm: boolean;
};
type LightTelemetry = {
  spectrum: string;
  hours_today: number;
};
type HistoryPoint = {
  ts: string;
  light: number;
};
type HistoryResponse = {
  points: HistoryPoint[];
};

export default function PlantLight() {
  const { data: activePlant, isLoading: loadingPlants, error: plantsError } = useSWR<PlantInstance | null>(
    "/plants/active",
    fetcher,
    {
    refreshInterval: 60000,
    }
  );

  const {
    data: light,
    isLoading: loadingLight,
    error: lightError,
  } = useSWR<PlantLight>(activePlant ? `/plants/${activePlant.id}/light` : null, fetcher, { refreshInterval: 30000 });
  const { data: lightTelemetry, isLoading: loadingTelemetry, error: telemetryError } = useSWR<LightTelemetry>(
    "/light",
    fetcher,
    { refreshInterval: 30000 }
  );
  const { data: history, isLoading: loadingHistory } = useSWR<HistoryResponse>("/history", fetcher, {
    refreshInterval: 30000,
  });

  const isLoading = loadingPlants || loadingLight || loadingTelemetry || loadingHistory;
  const hasError = plantsError || lightError || telemetryError;

  const spectrum = (lightTelemetry?.spectrum ?? "").trim().toLowerCase();
  const hasLiveLight = Boolean(spectrum);
  const lightVisual = spectrum === "blue"
    ? { label: "Blue", icon: "/assets/icons/lamp_blue.png" }
    : spectrum.includes("white")
      ? { label: "White", icon: "/assets/icons/lamp_white.png" }
      : spectrum === "red"
        ? { label: "Red", icon: "/assets/icons/lamp_red.png" }
        : { label: "Off", icon: "/assets/icons/lamp_off.png" };
  const latestLux = history?.points?.[history.points.length - 1]?.light;
  const luxLabel = latestLux !== undefined ? `${latestLux.toFixed(1)} lux` : "N/A";

  const spectrumColors: Record<string, string> = {
    blue:  "bg-blue-200/60",
    red:   "bg-red-200/60",
    white: "bg-slate-200/60",
    off:   "bg-gray-100",
  };

  // Pick by checking spectrum (already trimmed/lowercased)
  const boxColor =
    spectrum === "blue"  ? spectrumColors.blue  :
    spectrum.includes("white") ? spectrumColors.white :
    spectrum === "red"   ? spectrumColors.red   :
    spectrumColors.off;

  if (hasError) return <div className="card text-red-600">Light status unavailable</div>;
  if (isLoading) return <div className="card">Loading light status…</div>;
  if (!activePlant) return <div className="card">Light is off until a new plant starts.</div>;
  if (!light) return <div className="card text-red-600">Light data missing</div>;

  return (
    <div className="card relative h-full">
      <Image
        src={lightVisual.icon}
        alt={`${lightVisual.label} lamp`}
        width={64}
        height={64}
        className="absolute right-4 -top-0.5 h-20 w-20 object-contain"
        priority
      />

      <div className="mb-1">
        <p className="label">Light Status</p>
      </div>

      <div className="space-y-0.5">
        <p className="text-sm text-slate-500 leading-tight">Color</p>
        <p className="text-2xl font-semibold leading-tight">{lightVisual.label}</p>
      </div>

      <div className={`mt-2 rounded-lg ${boxColor} px-3 py-2`}>
        <p className="text-xs uppercase tracking-wide text-slate-500">Light intensity (KY-018)</p>
        <p className="text-xl font-semibold text-slate-900">{luxLabel}</p>
        <p className="mt-1 text-xs text-slate-500">Collected via KY-018 (LDR ADC) + MQTT /autogrow/sensors</p>
      </div>

      <p className="mt-2 text-sm text-emerald-700">
        {hasLiveLight ? "Auto-sync enabled" : "No active light output"}
      </p>
    </div>
  );
}
