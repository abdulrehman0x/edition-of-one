"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "eoo.reader_id";

function generateId(): string {
  return "reader-" + Math.random().toString(36).slice(2, 10);
}

export function getReaderId(): string {
 if (typeof window === "undefined") return "";
 const existing = window.localStorage.getItem(STORAGE_KEY);
 if (existing) return existing;
    const fresh = generateId();
    window.localStorage.setItem(STORAGE_KEY, fresh);
    return fresh;
}

export function setReaderId(id: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, id);
}

export function clearReaderId(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

export function useReader(): [string, (id: string) => void] {
  const [id, setId] = useState<string>("");
  useEffect(() => {
    setId(getReaderId());
  }, []);
  const update = useCallback((next: string) => {
    setReaderId(next);
    setId(next);
  }, []);
  return [id, update];
}
