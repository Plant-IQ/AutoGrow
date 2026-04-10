export const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const DEFAULT_LAT = process.env.NEXT_PUBLIC_DEFAULT_LAT ?? "13.7563";
export const DEFAULT_LON = process.env.NEXT_PUBLIC_DEFAULT_LON ?? "100.5018";

export const fetcher = (url: string) => fetch(`${BASE}${url}`).then((r) => r.json());

export const postJson = (path: string, body: unknown) =>
  fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
