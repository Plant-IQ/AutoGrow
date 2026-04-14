"use client";
import useSWR from "swr";
import { fetcher, DEFAULT_LAT, DEFAULT_LON } from "@/lib/api";

type WeatherContext = {
  temp_c?: number;
  humidity?: number;
  sunrise_utc?: string;
  sunset_utc?: string;
  source?: string;
};

export default function WeatherCard() {
  const { data, isLoading, error } = useSWR<WeatherContext>(
    `/context/weather?lat=${DEFAULT_LAT}&lon=${DEFAULT_LON}`,
    fetcher,
    { refreshInterval: 15 * 60 * 1000 }
  );

  if (isLoading) return <div className="card">Loading weather…</div>;
  if (error || !data) return <div className="card text-red-600">Weather unavailable</div>;

  const temp = data.temp_c !== undefined ? `${data.temp_c.toFixed(1)}°C` : "–°C";
  const humidity = data.humidity !== undefined ? `${data.humidity.toFixed(0)}% RH` : "–% RH";
  const sunrise = data.sunrise_utc
    ? new Date(data.sunrise_utc).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : "–";
  const sunset = data.sunset_utc
    ? new Date(data.sunset_utc).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : "–";
  const source = data.source ?? "weather service";

  return (
    <div className="card space-y-3">
      <p className="label">Outdoor</p>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="border-black border- rounded-lg bg-[#85c78a]/20 px-3 py-2">
          <p className="text-xs uppercase tracking-wide text-slate-500">Temp</p>
          <p className="font-medium text-slate-800">{temp}</p>
        </div>
        <div className="rounded-lg bg-[#6fb2d2]/20 px-3 py-2">
          <p className="text-xs uppercase tracking-wide text-slate-500">Humidity</p>
          <p className="font-medium text-slate-800">{humidity}</p>
        </div>
        <div className="col-span-2 flex items-center justify-between gap-2 rounded-lg bg-[#ffb88d]/20 px-3 py-2">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Sunrise</p>
            <p className="font-medium text-slate-800">{sunrise}</p>
          </div>
          <img src="/assets/icons/sunrise.png" alt="Sunrise" className="h-12 w-12 object-contain ml-auto" />
        </div>
        <div className="col-span-2 flex items-center justify-between gap-2 rounded-lg bg-[#d78451]/20 px-3 py-2">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Sunset</p>
            <p className="font-medium text-slate-800">{sunset}</p>
          </div>
          <img src="/assets/icons/sunset.png" alt="Sunrise" className="h-12 w-12 object-contain ml-auto" />
        </div>
      </div>
      <p className="text-xs text-slate-500">via {source}</p>
    </div>
  );
}
