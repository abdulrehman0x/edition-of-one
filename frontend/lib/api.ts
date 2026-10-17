import type { Edition, Event, Profile } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

const TIMEOUT_MS = 6000;

async function timedFetch(input: string, init?: RequestInit): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    return await fetch(input, { ...init, signal: ctrl.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function safeJson<T>(res: Response): Promise<T | null> {
  try {
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

let sampleCache: Edition | null = null;

async function loadSample(): Promise<Edition | null> {
  if (sampleCache) return sampleCache;
  try {
    const res = await fetch("/sample-edition.json");
    if (!res.ok) return null;
    const data = (await res.json()) as Edition;
    sampleCache = data;
    return data;
  } catch {
    return null;
  }
}

export interface EditionResult {
  edition: Edition | null;
  offline: boolean;
}

export async function getEdition(
  readerId: string,
  date: string
): Promise<EditionResult> {
  try {
    const res = await timedFetch(
      `${API_BASE}/edition/${encodeURIComponent(readerId)}?date=${encodeURIComponent(date)}`,
      { cache: "no-store" }
    );
    if (!res.ok) throw new Error(`status ${res.status}`);
    const data = await safeJson<Edition>(res);
    if (data) return { edition: data, offline: false };
  } catch {
    /* fall through to the bundled sample */
  }
  const sample = await loadSample();
  return { edition: sample, offline: true };
}

export async function getProfile(readerId: string): Promise<Profile | null> {
  try {
    const res = await timedFetch(
      `${API_BASE}/profile/${encodeURIComponent(readerId)}`,
      { cache: "no-store" }
    );
    if (!res.ok) return null;
    return await safeJson<Profile>(res);
  } catch {
    return null;
  }
}

export async function getArchive(
  readerId: string
): Promise<{ dates: string[] }> {
  try {
    const res = await timedFetch(
      `${API_BASE}/archive/${encodeURIComponent(readerId)}`,
      { cache: "no-store" }
    );
    if (!res.ok) return { dates: [] };
    const data = await safeJson<{ dates: string[] }>(res);
    return data || { dates: [] };
  } catch {
    return { dates: [] };
  }
}

export async function postOnboarding(payload: {
  reader_id: string;
  name: string;
  interests: string[];
  loves?: string[];
  reading_time?: string;
  location: string;
  tone: string;
}): Promise<Profile | null> {
  try {
    const res = await timedFetch(`${API_BASE}/onboarding`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) return null;
    return await safeJson<Profile>(res);
  } catch {
    return null;
  }
}

export async function postEvent(ev: Event): Promise<void> {
  try {
    await timedFetch(`${API_BASE}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(ev),
      keepalive: true,
    });
  } catch {
    /* tracking must never break reading */
  }
}

export async function advanceNight(readerId: string): Promise<boolean> {
  try {
    // Learning plus an edition rebuild can take a few seconds.
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 30000);
    try {
      const res = await fetch(
        `${API_BASE}/profile/${encodeURIComponent(readerId)}/advance`,
        { method: "POST", signal: ctrl.signal }
      );
      return res.ok;
    } finally {
      clearTimeout(timer);
    }
  } catch {
    return false;
  }
}

export async function removeTopic(
  readerId: string,
  topic: string
): Promise<Profile | null> {
  try {
    const res = await timedFetch(
      `${API_BASE}/profile/${encodeURIComponent(readerId)}/topics/${encodeURIComponent(topic)}`,
      { method: "DELETE" }
    );
    if (!res.ok) return null;
    return await safeJson<Profile>(res);
  } catch {
    return null;
  }
}

export { API_BASE };
