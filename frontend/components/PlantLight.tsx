"use client";
import useSWR from "swr";
import { fetcher, postJson } from "@/lib/api";

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

export default function PlantLight() {
  const { data: plants, isLoading: loadingPlants, error: plantsError } = useSWR<PlantInstance[]>("/plants/", fetcher, {
    refreshInterval: 60000,
  });

  const activePlant = plants?.[0];

  const {
    data: light,
    isLoading: loadingLight,
    mutate,
    error: lightError,
  } = useSWR<PlantLight>(activePlant ? `/plants/${activePlant.id}/light` : null, fetcher, { refreshInterval: 30000 });

  const isLoading = loadingPlants || loadingLight;
  const hasError = plantsError || lightError;

  async function handleConfirm() {
    if (!activePlant) return;
    await postJson(`/plants/${activePlant.id}/confirm-transition`, {});
    mutate();
  }

  if (hasError) return <div className="card text-red-600">Light status unavailable</div>;
  if (isLoading) return <div className="card">Loading light status…</div>;
  if (!activePlant) return <div className="card">No plants defined yet.</div>;
  if (!light) return <div className="card text-red-600">Light data missing</div>;

  const stageLabel = ["Seed", "Veg", "Bloom"][Math.min(light.stage, 2)] ?? `Stage ${light.stage}`;

  return (
    <div className="card gap-3">
      <div className="flex items-center justify-between">
        <p className="label">Light program</p>
        <span className="text-xs text-slate-500">{activePlant.label}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="h-12 w-12 rounded-full border border-[color:var(--brand-primary)]/30 shadow-inner" style={{ background: light.color }} />
        <div>
          <p className="text-sm text-slate-500">Current color</p>
          <p className="text-lg font-semibold">{light.color}</p>
          <p className="text-xs text-slate-500">Stage: {stageLabel}</p>
        </div>
      </div>

      {light.pending_confirm ? (
        <div className="flex items-center justify-between gap-3 rounded-lg bg-amber-50 px-3 py-2 text-amber-800">
          <div>
            <p className="text-sm font-medium">Stage change pending</p>
            <p className="text-xs">Confirm to advance and update the light color.</p>
          </div>
          <button className="btn !px-3 !py-2 !text-sm" onClick={handleConfirm}>
            Confirm stage
          </button>
        </div>
      ) : (
        <p className="text-sm text-emerald-700">Stage synced · no confirmation needed</p>
      )}
    </div>
  );
}
