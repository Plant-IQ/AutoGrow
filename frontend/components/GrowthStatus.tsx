"use client";
import Image from "next/image";
import useSWR, { mutate } from "swr";
import { useState, FormEvent, useRef, useEffect } from "react";
import { fetcher, postJson } from "@/lib/api";

type StageResponse = {
  stage: number;
  label: string;
  days_in_stage: number;
};

type HarvestResponse = {
  days_to_harvest: number;
  projected_date: string;
};

const STAGE_LABELS = ["Seed", "Veg", "Bloom"];
const ICONS = [
  "/assets/icons/state_seed.png",
  "/assets/icons/state_veg.png",
  "/assets/icons/state_bloom.png",
];

const PLANT_DB: { name: string; seed: number; veg: number; bloom: number }[] = [
  { name: "Sunflower Microgreens", seed: 3, veg: 4, bloom: 0 },
  { name: "Pea Shoots", seed: 3, veg: 7, bloom: 0 },
  { name: "Radish Microgreens", seed: 2, veg: 5, bloom: 0 },
  { name: "Broccoli Microgreens", seed: 2, veg: 6, bloom: 0 },
  { name: "Mustard Microgreens", seed: 3, veg: 5, bloom: 0 },
  { name: "Green Oak Lettuce", seed: 5, veg: 35, bloom: 0 },
  { name: "Red Oak Lettuce", seed: 5, veg: 35, bloom: 0 },
  { name: "Cos / Romaine Lettuce", seed: 5, veg: 40, bloom: 0 },
  { name: "Butterhead Lettuce", seed: 5, veg: 40, bloom: 0 },
  { name: "Frillice Iceberg", seed: 5, veg: 40, bloom: 0 },
  { name: "Arugula / Rocket", seed: 4, veg: 30, bloom: 0 },
  { name: "Mizuna", seed: 4, veg: 35, bloom: 0 },
  { name: "Swiss Chard", seed: 6, veg: 45, bloom: 0 },
  { name: "Red Coral Lettuce", seed: 5, veg: 35, bloom: 0 },
  { name: "Bok Choy", seed: 4, veg: 30, bloom: 0 },
  { name: "Kale", seed: 5, veg: 45, bloom: 0 },
  { name: "Spinach", seed: 5, veg: 35, bloom: 0 },
  { name: "Water Spinach (Morning Glory)", seed: 3, veg: 20, bloom: 0 },
  { name: "Chinese Broccoli (Gai Lan)", seed: 5, veg: 40, bloom: 0 },
  { name: "Tatsoi", seed: 4, veg: 30, bloom: 0 },
  { name: "Watercress", seed: 5, veg: 40, bloom: 0 },
  { name: "Mini Napa Cabbage", seed: 5, veg: 45, bloom: 0 },
  { name: "Chinese Mustard Green", seed: 4, veg: 35, bloom: 0 },
  { name: "Brussels Sprouts", seed: 6, veg: 50, bloom: 0 },
  { name: "Holy Basil", seed: 7, veg: 30, bloom: 0 },
  { name: "Thai Basil", seed: 7, veg: 30, bloom: 0 },
  { name: "Mint", seed: 10, veg: 40, bloom: 0 },
  { name: "Coriander / Cilantro", seed: 7, veg: 40, bloom: 0 },
  { name: "Spring Onion / Scallion", seed: 5, veg: 35, bloom: 0 },
  { name: "Parsley", seed: 10, veg: 45, bloom: 0 },
  { name: "Rosemary", seed: 14, veg: 60, bloom: 0 },
  { name: "Thyme", seed: 10, veg: 50, bloom: 0 },
  { name: "Oregano", seed: 10, veg: 50, bloom: 0 },
  { name: "Dill", seed: 7, veg: 35, bloom: 0 },
  { name: "Chives", seed: 10, veg: 40, bloom: 0 },
  { name: "Lemon Balm", seed: 10, veg: 40, bloom: 0 },
  { name: "Sage", seed: 10, veg: 45, bloom: 0 },
  { name: "Sweet Basil", seed: 7, veg: 35, bloom: 0 },
  { name: "Celery", seed: 10, veg: 45, bloom: 0 },
  { name: "Cherry Tomato", seed: 7, veg: 30, bloom: 45 },
  { name: "Bird's Eye Chili (Thai Chili)", seed: 10, veg: 40, bloom: 40 },
  { name: "Mini Sweet Pepper", seed: 10, veg: 40, bloom: 45 },
  { name: "Bush Bean", seed: 5, veg: 25, bloom: 20 },
  { name: "Strawberry", seed: 14, veg: 45, bloom: 30 },
  { name: "Red Radish", seed: 4, veg: 25, bloom: 0 },
  { name: "Baby Carrot", seed: 7, veg: 45, bloom: 0 },
  { name: "Thai Eggplant", seed: 7, veg: 40, bloom: 40 },
  { name: "Bush Cucumber", seed: 5, veg: 30, bloom: 25 },
  { name: "Zucchini", seed: 6, veg: 35, bloom: 25 },
  { name: "Jalapeño Pepper", seed: 10, veg: 40, bloom: 45 },
];

export default function GrowthStatus() {
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [seedDays, setSeedDays] = useState(7);
  const [vegDays, setVegDays] = useState(21);
  const [bloomDays, setBloomDays] = useState(28);

  const [suggestions, setSuggestions] = useState<typeof PLANT_DB>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const suggestRef = useRef<HTMLUListElement>(null);

  const { data: stage, isLoading: stageLoading, error: stageError } = useSWR<StageResponse>("/stage", fetcher, {
    refreshInterval: 30000,
  });
  const { data: harvest, isLoading: harvestLoading, error: harvestError } = useSWR<HarvestResponse>(
    "/harvest-eta",
    fetcher,
    { refreshInterval: 60000 },
  );

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (suggestRef.current && !suggestRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  function handleNameChange(val: string) {
    setName(val);
    setActiveIdx(-1);
    if (!val.trim()) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }
    const q = val.toLowerCase();
    const filtered = PLANT_DB.filter((p) => p.name.toLowerCase().includes(q));
    setSuggestions(filtered);
    setShowSuggestions(filtered.length > 0);
  }

  function selectPlant(plant: (typeof PLANT_DB)[0]) {
    setName(plant.name);
    setSeedDays(plant.seed);
    setVegDays(plant.veg);
    setBloomDays(plant.bloom);
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

  if (stageLoading || harvestLoading) return <div className="card">Loading growth status…</div>;
  if (stageError || harvestError || !stage || !harvest)
    return <div className="card text-red-600">Growth status unavailable</div>;

  const idx = Math.min(Math.max(stage.stage, 0), 2);
  let icon = ICONS[idx] ?? ICONS[2];
  const stageName = stage.label || STAGE_LABELS[idx] || "Stage";

  const projected = new Date(harvest.projected_date).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });

  const labelLower = stageName.toLowerCase();
  let progress = 0;
  if (labelLower.includes("seed") || labelLower.includes("germ")) {
    icon = ICONS[0];
    progress = 0;
  } else if (labelLower.includes("veg")) {
    icon = ICONS[1];
    progress = 0.5;
  } else if (labelLower.includes("bloom") || labelLower.includes("flower") || labelLower.includes("fruit")) {
    icon = ICONS[2];
    progress = 1;
  } else {
    progress = Math.min(idx / 2, 1);
  }
  const percent = Math.round(progress * 100);

  async function handleHarvest(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const typeRes = await postJson("/plant-types", {
        name: name || "New plant",
        stage_durations_days: [seedDays, vegDays, bloomDays],
        stage_colors: ["#4DA6FF", "#FFFFFF", "#FF6FA3"],
      });
      if (!typeRes.ok) throw new Error("Failed to save plant type");
      const type = await typeRes.json();

      const plantRes = await postJson("/plants/", {
        label: name || "New plant",
        plant_type_id: type.id,
      });
      if (!plantRes.ok) throw new Error("Failed to create plant");
      const plant = await plantRes.json();

      const resetRes = await postJson("/stage/reset", {
        name: name || "New plant",
        plant_id: plant.id,
        seed_days: seedDays,
        veg_days: vegDays,
        bloom_days: bloomDays,
      });
      if (!resetRes.ok) throw new Error("Failed to reset stage");

      mutate("/stage");
      mutate("/plants/");
      setMessage("Harvested and started new grow");
      setShowForm(false);
      setName("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Could not harvest/start";
      setMessage(msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="status-frame h-full">
      <div className="status-card h-full" style={{ minHeight: "100px" }}>
        <div className="status-header">
          <span className="day-label">Day</span>
          <div className="status-divider" aria-hidden />
          <span className="status-eyebrow">Growth status</span>
          <Image src={icon} alt={stageName} width={88} height={88} className="status-icon" priority />
          <span className="day-number">{stage.days_in_stage}</span>
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
            <div className="status-bar-fill" style={{ width: `${percent}%` }} />
          </div>
          <div className="status-meta mt-2">
            <span>
              {harvest.days_to_harvest} days to harvest · {projected}
            </span>
            {!showForm && (
              <button className="status-harvest-btn" onClick={() => setShowForm(true)}>
                Harvest
              </button>
            )}
          </div>
        </div>

        {showForm && (
          <form className="status-form" onSubmit={handleHarvest}>
            <div className="grid grid-cols-1 gap-2">
              <label className="field">
                <span>Next plant name</span>
                <div style={{ position: "relative" }}>
                  <input
                    value={name}
                    onChange={(e) => handleNameChange(e.target.value)}
                    onKeyDown={handleKeyDown}
                    onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
                    placeholder="e.g., Basil"
                    autoComplete="off"
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
                        boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)",
                      }}
                    >
                      {suggestions.map((p, i) => (
                        <li
                          key={p.name}
                          onMouseDown={() => selectPlant(p)}
                          style={{
                            padding: "8px 12px",
                            cursor: "pointer",
                            fontSize: "14px",
                            background: i === activeIdx ? "#f3f4f6" : "transparent",
                            display: "flex",
                            justifyContent: "space-between",
                          }}
                        >
                          <span>{p.name}</span>
                          <span style={{ color: "#6b7280", fontSize: "12px" }}>
                            {p.seed + p.veg + p.bloom}d
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </label>

              <div className="grid grid-cols-3 gap-2">
                <label className="field">
                  <span>Seed days</span>
                  <input
                    type="number"
                    min={1}
                    value={seedDays}
                    onChange={(e) => setSeedDays(parseInt(e.target.value) || 1)}
                  />
                </label>
                <label className="field">
                  <span>Veg days</span>
                  <input
                    type="number"
                    min={1}
                    value={vegDays}
                    onChange={(e) => setVegDays(parseInt(e.target.value) || 1)}
                  />
                </label>
                <label className="field">
                  <span>Bloom days</span>
                  <input
                    type="number"
                    min={0}
                    value={bloomDays}
                    onChange={(e) => setBloomDays(parseInt(e.target.value) || 0)}
                  />
                </label>
              </div>
            </div>
            <div className="status-form-actions">
              <button type="submit" className="status-harvest-btn" disabled={saving}>
                {saving ? "Saving…" : "Harvest & start"}
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