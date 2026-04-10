"use client";
import Image from "next/image";
import useSWR, { mutate } from "swr";
import { useEffect, useRef, useState } from "react";
import { fetcher, postJson, DEFAULT_LAT, DEFAULT_LON } from "@/lib/api";

type StageResponse = { stage: number; label: string; days_in_stage: number };
type HarvestResponse = { days_to_harvest: number; projected_date: string };
type PlantType = { id: number; name: string; stage_durations_days: number[] };
type ActivePlant = { id: number; session_code: string; label: string; plant_type_id: number };
type WeatherContext = {
  temp_c?: number;
  apparent_temp_c?: number;
  humidity?: number;
  wind_speed_mps?: number;
  sunrise_utc?: string;
  sunset_utc?: string;
  source?: string;
};

const STAGE_LABELS = ["Seed", "Veg", "Bloom"];
const ICONS = ["/assets/icons/state_seed.png", "/assets/icons/state_veg.png", "/assets/icons/state_bloom.png"];
export default function GrowthStatus() {
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [suggestions, setSuggestions] = useState<PlantType[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const suggestRef = useRef<HTMLUListElement>(null);

  const { data: activePlant, isLoading: activeLoading, error: activeError } = useSWR<ActivePlant | null>(
    "/plants/active",
    fetcher,
    { refreshInterval: 30000 }
  );
  const { data: stage } = useSWR<StageResponse>(activePlant ? "/stage" : null, fetcher, { refreshInterval: 30000 });
  const { data: harvest } = useSWR<HarvestResponse>(activePlant ? "/harvest-eta" : null, fetcher, {
    refreshInterval: 60000,
  });
  const { data: plantTypes } = useSWR<PlantType[]>("/plant-types", fetcher, { refreshInterval: 300000 });
  const { data: weather } = useSWR<WeatherContext>(
    `/context/weather?lat=${DEFAULT_LAT}&lon=${DEFAULT_LON}`,
    fetcher,
    { refreshInterval: 15 * 60 * 1000 }
  );

  useEffect(() => {
    if (!activePlant) setShowForm(true);
  }, [activePlant]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (suggestRef.current && !suggestRef.current.contains(e.target as Node)) setShowSuggestions(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  function handleNameChange(val: string) {
    setName(val);
    setActiveIdx(-1);
    if (!val.trim() || !plantTypes) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }
    const q = val.toLowerCase();
    const filtered = plantTypes.filter((p) => p.name.toLowerCase().includes(q)).slice(0, 12);
    setSuggestions(filtered);
    setShowSuggestions(filtered.length > 0);
  }

  function selectPlant(plant: PlantType) {
    setName(plant.name);
    setSuggestions([]);
    setShowSuggestions(false);
    setActiveIdx(-1);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!showSuggestions || suggestions.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && activeIdx >= 0) {
      e.preventDefault();
      selectPlant(suggestions[activeIdx]);
    } else if (e.key === "Escape") {
      setShowSuggestions(false);
    }
  }

  async function handleHarvest() {
    setSaving(true);
    setMessage(null);
    try {
      const res = await postJson("/plants/harvest-active", {});
      if (!res.ok) throw new Error("Failed to harvest active plant");
      await Promise.all([
        mutate("/plants/active"),
        mutate("/stage"),
        mutate("/harvest-eta"),
        mutate("/history"),
        mutate("/pump-status"),
        mutate("/light"),
        mutate("/health"),
      ]);
      setShowForm(true);
      setMessage("Harvest complete. Start a new plant when ready.");
    } catch (err: unknown) {
      setMessage(err instanceof Error ? err.message : "Could not harvest");
    } finally {
      setSaving(false);
    }
  }

  async function handleStart(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const trimmed = name.trim();
      const startRes = await postJson("/plants/start", { name: name.trim() });
      if (!startRes.ok) throw new Error("Plant not found in database");
      const plant = await startRes.json();
      const type = plantTypes?.find((t) => t.id === plant.plant_type_id);
      const d = type?.stage_durations_days ?? [7, 21, 0];
      await postJson("/stage/reset", {
        name: name.trim(),
        plant_id: plant.id,
        seed_days: d[0] ?? 7,
        veg_days: d[1] ?? 21,
        bloom_days: d[2] ?? 0,
      });
      await Promise.all([mutate("/plants/active"), mutate("/stage"), mutate("/harvest-eta"), mutate("/plants/")]);
      setName(trimmed);
      setShowForm(false);
      setMessage("Started new grow session.");
    } catch (err: unknown) {
      setMessage(err instanceof Error ? err.message : "Could not start grow");
    } finally {
      setSaving(false);
    }
  }

  if (activeLoading) return <div className="card">Loading growth status…</div>;
  if (activeError) return <div className="card text-red-600">Growth status unavailable</div>;

  const hasActive = Boolean(activePlant && stage && harvest);
  const stageSafe = stage ?? { stage: 0, label: "", days_in_stage: 0 };
  const harvestSafe = harvest ?? { days_to_harvest: 0, projected_date: new Date(0).toISOString() };
  const idx = hasActive ? Math.min(Math.max(stageSafe.stage, 0), 2) : 0;
  const stageName = hasActive ? stageSafe.label || STAGE_LABELS[idx] : "No active plant";
  const icon = ICONS[idx] ?? ICONS[0];
  const progress = hasActive ? Math.round((idx / 2) * 100) : 0;
  const projected = hasActive
    ? new Date(harvestSafe.projected_date).toLocaleDateString(undefined, { month: "short", day: "numeric" })
    : "";
  const sunrise = weather?.sunrise_utc ? new Date(weather.sunrise_utc).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : null;
  const sunset = weather?.sunset_utc ? new Date(weather.sunset_utc).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : null;
  const tempDisplay = weather?.temp_c !== undefined ? `${weather.temp_c.toFixed(1)}°C` : "–°C";
  const humidityDisplay = weather?.humidity !== undefined ? `${weather.humidity.toFixed(0)}% RH` : "–% RH";

  return (
    <div className="status-frame h-full">
      <div className="status-card h-full" style={{ minHeight: "100px" }}>
        <div className="status-header">
          <span className="day-label">Day</span>
          <div className="status-divider" aria-hidden />
          <span className="status-eyebrow">Growth status</span>
          {hasActive && <Image src={icon} alt={stageName} width={88} height={88} className="status-icon" priority />}
          <span className="day-number">{hasActive ? stageSafe.days_in_stage : "-"}</span>
          <p className="status-title" style={{ marginTop: "-4px" }}>
            {stageName}
          </p>
        </div>

        <div className="status-progress mt-auto">
          <div className="status-steps">
            <span>Seed</span>
            <span>Veg</span>
            <span>Bloom</span>
          </div>
          <div className="status-bar">
            <div className="status-bar-fill" style={{ width: `${progress}%` }} />
          </div>
          <div className="status-meta mt-2">
            <span>{hasActive ? `${harvestSafe.days_to_harvest} days to harvest · ${projected}` : "Awaiting next plant"}</span>
            {hasActive && (
              <button className="status-harvest-btn" onClick={handleHarvest} disabled={saving}>
                {saving ? "Saving…" : "Harvest"}
              </button>
            )}
          </div>
          {weather && (
            <div className="status-meta mt-2 text-sm text-slate-600">
              <span>
                Outdoor {tempDisplay} / {humidityDisplay}
                {sunrise && sunset ? ` · Sunrise ${sunrise} · Sunset ${sunset}` : ""}
                {weather.source ? ` · via ${weather.source}` : ""}
              </span>
            </div>
          )}
        </div>

        {showForm && (
          <form className="status-form" onSubmit={handleStart}>
            <label className="field w-full">
              <span>Plant name</span>
              <div style={{ position: "relative", width: "100%" }}>
                <input
                  value={name}
                  onChange={(e) => handleNameChange(e.target.value)}
                  onKeyDown={handleKeyDown}
                  onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
                  placeholder="e.g., Water Spinach (Morning Glory)"
                  autoComplete="off"
                  required
                  style={{ width: "100%" }}
                />
                {showSuggestions && (
                  <ul
                    ref={suggestRef}
                    style={{
                      position: "absolute",
                      top: "100%",
                      left: 0,
                      right: 0,
                      background: "var(--card-bg, #fff)",
                      border: "1px solid #d1d5db",
                      borderRadius: "0.375rem",
                      maxHeight: "200px",
                      overflowY: "auto",
                      zIndex: 50,
                      margin: "2px 0 0",
                      padding: 0,
                      listStyle: "none",
                    }}
                  >
                    {suggestions.map((p, i) => (
                      <li
                        key={p.id}
                        onMouseDown={() => selectPlant(p)}
                        style={{
                          padding: "8px 12px",
                          cursor: "pointer",
                          fontSize: "14px",
                          background: i === activeIdx ? "#f3f4f6" : "transparent",
                        }}
                      >
                        {p.name}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </label>
            <div className="status-form-actions">
              <button type="submit" className="status-harvest-btn" disabled={saving}>
                {saving ? "Saving…" : "Start plant"}
              </button>
              <button type="button" className="status-secondary-btn" onClick={() => setShowForm(false)} disabled={saving}>
                Cancel
              </button>
            </div>
            {message && <p className="status-message">{message}</p>}
          </form>
        )}
      </div>
    </div>
  );
}
