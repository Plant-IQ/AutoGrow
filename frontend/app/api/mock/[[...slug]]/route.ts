import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

type HistoryPoint = {
  ts: string;
  soil: number;
  temp: number;
  humidity: number;
  light: number;
  stage: number;
  stage_name: string;
  spectrum: string;
  pump_on: boolean;
  pump_status: string;
  light_hrs_today: number;
  harvest_eta_days: number;
  health_score: number;
};

// In-memory mock state for quick UI dev
let activePlant:
  | {
      id: number;
      session_code: string;
      label: string;
      plant_type_id: number;
      current_stage_index: number;
      stage_started_at: string;
      pending_confirm: boolean;
    }
  | null = {
  id: 1,
  session_code: "ABC123",
  label: "Basil",
  plant_type_id: 1,
  current_stage_index: 1,
  stage_started_at: new Date(Date.now() - 8 * 24 * 60 * 60 * 1000).toISOString(),
  pending_confirm: false,
};

let plantTypes = [
  { id: 1, name: "Default 3-stage", stage_durations_days: [7, 21, 30] },
  { id: 2, name: "Leafy quick", stage_durations_days: [5, 14, 0] },
];

let stage = { stage: 1, label: "Veg", days_in_stage: 8 };
let harvest = {
  days_to_harvest: 22,
  projected_date: new Date(Date.now() + 22 * 24 * 60 * 60 * 1000).toISOString(),
};

let health = {
  score: 84,
  components: { water: 0.82, light: 0.9, nutrients: 0.7, airflow: 0.65 },
};

let pumpStatus = {
  ok: true,
  vibration: 0.12,
  last_checked: new Date().toISOString(),
};

let lightTelemetry = {
  spectrum: "white",
  hours_today: 8.5,
};

let plantLight = {
  plant_id: 1,
  stage: 1,
  color: "#aafc9d",
  pending_confirm: false,
};

let history: HistoryPoint[] = Array.from({ length: 48 }).map((_, i) => {
  const ts = new Date(Date.now() - (47 - i) * 30 * 60 * 1000);
  return {
    ts: ts.toISOString(),
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
    harvest_eta_days: harvest.days_to_harvest,
    health_score: health.score,
  };
});

let observations: any[] = [];

function ok(body: unknown, init: number | ResponseInit = 200) {
  return NextResponse.json(body, typeof init === "number" ? { status: init } : init);
}

export async function GET(req: NextRequest, { params }: { params: { slug?: string[] } }) {
  const path = "/" + (params.slug ?? []).join("/");
  const lightMatch = path.match(/^\/plants\/(\d+)\/light$/);
  const confirmMatch = path.match(/^\/plants\/(\d+)\/confirm-transition$/);

  switch (path) {
    case "/plants/active":
      return ok(activePlant);
    case "/plants":
    case "/plants/":
      return ok(activePlant ? [activePlant] : []);
    case "/stage":
      return ok(stage);
    case "/harvest-eta":
      return ok(harvest);
    case "/plant-types":
      return ok(plantTypes);
    case "/light":
      return ok(lightTelemetry);
    case "/pump-status":
      return ok(pumpStatus);
    case "/health":
      return ok(health);
    case "/history":
      return ok({ points: history });
    case "/context/weather":
      return ok({
        temp_c: 33.9,
        apparent_temp_c: 36.1,
        humidity: 53,
        wind_speed_mps: 2.7,
        sunrise_utc: new Date(new Date().setHours(23, 5, 0, 0)).toISOString(),
        sunset_utc: new Date(new Date().setHours(11, 30, 0, 0)).toISOString(),
        source: "openweathermap",
      });
    default:
      if (lightMatch) return ok(plantLight);
      if (confirmMatch) return ok({ ok: true });
      return ok({ message: `No mock for ${path}`, slug: params.slug }, 404);
  }
}

export async function POST(req: NextRequest, { params }: { params: { slug?: string[] } }) {
  const path = "/" + (params.slug ?? []).join("/");
  const body = req.method === "POST" ? await req.json().catch(() => ({})) : {};
  const confirmMatch = path.match(/^\/plants\/(\d+)\/confirm-transition$/);

  switch (path) {
    case "/plants/start": {
      const name = (body.name as string)?.trim() || "New Plant";
      activePlant = {
        id: 1,
        session_code: Math.random().toString(36).slice(2, 8).toUpperCase(),
        label: name,
        plant_type_id: plantTypes[0].id,
        current_stage_index: 0,
        stage_started_at: new Date().toISOString(),
        pending_confirm: false,
      };
      stage = { stage: 0, label: "Seed", days_in_stage: 1 };
      harvest = {
        days_to_harvest: 42,
        projected_date: new Date(Date.now() + 42 * 24 * 60 * 60 * 1000).toISOString(),
      };
      return ok(activePlant, 201);
    }
    case "/stage/reset": {
      stage = { stage: 0, label: "Seed", days_in_stage: 1 };
      return ok(stage);
    }
    case "/plants/harvest-active": {
      activePlant = null;
      stage = { stage: 0, label: "", days_in_stage: 0 };
      plantLight = { ...plantLight, pending_confirm: false };
      return ok({ ok: true, message: "Harvested" });
    }
    case "/light": {
      lightTelemetry = { ...lightTelemetry, ...body };
      return ok(lightTelemetry);
    }
    case "/observations": {
      const id = observations.length + 1;
      observations.push({ id, ...body, ts: new Date().toISOString() });
      return ok({ id, ok: true }, 201);
    }
    default:
      if (confirmMatch) {
        plantLight = { ...plantLight, pending_confirm: false };
        return ok({ ok: true });
      }
      return ok({ message: `No mock for ${path}`, slug: params.slug }, 404);
  }
}
