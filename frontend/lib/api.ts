const REAL_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const MOCK_BASE = "/api/mock"; // kept for compatibility, but we also have inline mocks

async function fetchJson(path: string, base: string) {
  const res = await fetch(`${base}${path}`);
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

export const realFetcher = async (path: string) => fetchJson(path, REAL_BASE);

export const fetcher = async (path: string) => {
  try {
    const data = await fetchJson(path, REAL_BASE);
    if (shouldFallback(path, data) && REAL_BASE !== MOCK_BASE) {
      return inlineMock(path);
    }
    return data;
  } catch {
    return inlineMock(path);
  }
};

export const postJson = async (path: string, body: unknown) => {
  const doPost = (base: string) =>
    fetch(`${base}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

  try {
    const res = await doPost(REAL_BASE);
    if (res.ok) return res;
    throw new Error(`${res.status}`);
  } catch {
    return inlineMockResponse(path, body);
  }
};

// Kept for compatibility in case other code imports BASE directly
export const BASE = REAL_BASE;
export const DEFAULT_LAT = process.env.NEXT_PUBLIC_DEFAULT_LAT ?? "13.7563";
export const DEFAULT_LON = process.env.NEXT_PUBLIC_DEFAULT_LON ?? "100.5018";

// If the real API returns "empty" responses that hide UI panels, fall back to mock data.
function shouldFallback(path: string, data: unknown): boolean {
  const payload = data as {
    points?: unknown[];
    score?: number;
    components?: Record<string, unknown>;
  } | null;

  if (path === "/plants/active") return data == null;
  if (path === "/stage" || path === "/harvest-eta") return data == null;
  if (path === "/history") return Array.isArray(payload?.points) && payload.points.length === 0;
  if (path === "/health") {
    const score = payload?.score;
    const components = payload?.components;
    const emptyComponents = components && Object.keys(components).length === 0;
    return data == null || score == null || score <= 0 || emptyComponents;
  }
  return false;
}

// Inline mock payloads so we don't depend on API routes when backend is absent.
function inlineMock(path: string): unknown {
  const now = Date.now();
  const plant = {
    id: 1,
    session_code: "ABC123",
    label: "Basil",
    plant_type_id: 1,
    current_stage_index: 1,
    stage_started_at: new Date(now - 8 * 24 * 60 * 60 * 1000).toISOString(),
    pending_confirm: false,
  };

  const health = {
    score: 84,
    components: { water: 0.82, light: 0.9, nutrients: 0.7, airflow: 0.65 },
  };

  const historyPoints = Array.from({ length: 48 }).map((_, i) => {
    const ts = new Date(now - (47 - i) * 30 * 60 * 1000).toISOString();
    return {
      ts,
      soil: 52 + Math.sin(i / 6) * 5,
      temp: 25.5 + Math.sin(i / 5) * 1.2,
      humidity: 63 + Math.cos(i / 4) * 4,
      light: 360 + Math.sin(i / 3) * 40,
      stage: 1,
      stage_name: "Veg",
      spectrum: "veg",
      pump_on: i % 7 === 0,
      pump_status: "healthy",
      light_hrs_today: 9.1,
      harvest_eta_days: 22,
      health_score: health.score,
    };
  });

  const soilMoistureReadings = Array.from({ length: 32 }).map((_, i) => {
    const ts = new Date(now - (31 - i) * 45 * 60 * 1000).toISOString();
    return {
      ts,
      value: 36 + Math.sin(i / 4) * 8 + (i % 5 === 0 ? -3 : 0),
    };
  });

  const outdoorHumidityReadings = Array.from({ length: 34 }).map((_, i) => {
    const ts = new Date(now - (33 - i) * 42 * 60 * 1000).toISOString();
    return {
      ts,
      value: 58 + Math.cos(i / 5) * 10,
    };
  });

  const glasshouseTemperatureReadings = Array.from({ length: 32 }).map((_, i) => {
    const ts = new Date(now - (31 - i) * 45 * 60 * 1000).toISOString();
    return {
      ts,
      value: 28 + Math.sin(i / 4) * 2.8 + (i % 6 === 0 ? 1.1 : 0),
    };
  });

  const outdoorTemperatureReadings = Array.from({ length: 34 }).map((_, i) => {
    const ts = new Date(now - (33 - i) * 42 * 60 * 1000).toISOString();
    return {
      ts,
      value: 26 + Math.cos(i / 5) * 3.1,
    };
  });

  const glasshouseDailyAverages = Array.from({ length: 10 }).map((_, i) => {
    const day = new Date(now - (9 - i) * 24 * 60 * 60 * 1000);
    return {
      date: day.toISOString(),
      avg_temp: 26.4 + Math.sin(i / 3) * 1.6,
      avg_humidity: 61 + Math.cos(i / 3) * 5.5,
    };
  });

  const outdoorDailyAverages = Array.from({ length: 10 }).map((_, i) => {
    const day = new Date(now - (9 - i) * 24 * 60 * 60 * 1000);
    return {
      date: day.toISOString(),
      avg_temp: 24.8 + Math.cos(i / 3) * 1.9,
    };
  });

  const pumpVibrationReadings = Array.from({ length: 32 }).map((_, i) => {
    const ts = new Date(now - (31 - i) * 45 * 60 * 1000).toISOString();
    return {
      ts,
      value: i % 7 === 0 ? 0.18 : 0,
    };
  });

  const map: Record<string, unknown> = {
    "/plants/active": plant,
    "/plants": [plant],
    "/stage": { stage: 1, label: "Veg", days_in_stage: 8 },
    "/harvest-eta": {
      days_to_harvest: 22,
      projected_date: new Date(now + 22 * 24 * 60 * 60 * 1000).toISOString(),
    },
    "/plant-types": [
      { id: 1, name: "Default 3-stage", stage_durations_days: [7, 21, 30] },
      { id: 2, name: "Leafy quick", stage_durations_days: [5, 14, 0] },
    ],
    "/light": { spectrum: "white", hours_today: 8.5 },
    "/pump-status": { ok: true, vibration: 0.12, last_checked: new Date().toISOString() },
    "/health": health,
    "/history": { points: historyPoints },
    "/context/weather": {
      temp_c: 33.9,
      apparent_temp_c: 36.1,
      humidity: 53,
      wind_speed_mps: 2.7,
      sunrise_utc: new Date().toISOString(),
      sunset_utc: new Date().toISOString(),
      source: "openweathermap",
    },
    "/api/readings?field=soil_moisture": {
      points: soilMoistureReadings,
    },
    "/api/outdoor?field=humidity": {
      points: outdoorHumidityReadings,
    },
    "/api/readings?field=temperature": {
      points: glasshouseTemperatureReadings,
    },
    "/api/readings?field=pump_vibration": {
      points: pumpVibrationReadings,
    },
    "/api/outdoor?field=temp": {
      points: outdoorTemperatureReadings,
    },
    "/api/readings/daily-avg": glasshouseDailyAverages,
    "/api/outdoor/daily-avg": outdoorDailyAverages,
    "/plants/1/light": { plant_id: 1, stage: 1, color: "#aafc9d", pending_confirm: false },
  };

  if (map[path]) return map[path];
  return { ok: true, mock: true, path };
}

function inlineMockResponse(path: string, body: unknown): Response {
  if (path === "/plants/start") {
    const res = inlineMock("/plants/active");
    return new Response(JSON.stringify(res), { status: 201, headers: { "Content-Type": "application/json" } });
  }
  if (path === "/stage/reset" || path === "/plants/harvest-active" || path.includes("/confirm-transition")) {
    return new Response(JSON.stringify({ ok: true, mock: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }
  // fallback
  return new Response(JSON.stringify({ ok: true, mock: true, path, body }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
