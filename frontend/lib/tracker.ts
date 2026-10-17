"use client";

import { useEffect, useRef, type RefObject } from "react";
import { postEvent } from "./api";
import { getReaderId } from "./reader";
import type { Event, EventType } from "./types";

class Tracker {
 private queue: Event[] = [];
 private flushing = false;
 private batchSize = 5;

    track(
      event_type: EventType,
      article_id?: string | null,
      value = 1.0
    ): void {
      const ev: Event = {
        reader_id: getReaderId(),
        article_id: article_id || null,
        event_type,
        value,
      };
      this.queue.push(ev);
      if (this.queue.length >= this.batchSize) {
        void this.flush();
      }
    }

    async flush(): Promise<void> {
      if (this.flushing || this.queue.length === 0) return;
      this.flushing = true;
      const batch = this.queue.splice(0, this.queue.length);
      try {
        for (const ev of batch) {
          await postEvent(ev);
        }
      } catch {
        this.queue.push(...batch);
      } finally {
        this.flushing = false;
      }
    }
}

export const tracker = new Tracker();
if (typeof window !== "undefined") {
  window.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      void tracker.flush();
    }
  });
  window.addEventListener("beforeunload", () => {
    void tracker.flush();
  });
}

export function useImpression(
  ref: RefObject<HTMLElement>,
  articleId: string
): void {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined") return;
    const obs = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            tracker.track("impression", articleId, 1.0);
            obs.disconnect();
            break;
          }
        }
      },
      { threshold: 0.5 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [ref, articleId]);
}

export function useDwell(articleId: string | null, minSeconds = 1.5): void {
 const startRef = useRef<number | null>(null);
 useEffect(() => {
  if (!articleId) return;
  startRef.current = Date.now();
  const id = articleId;
  return () => {
   if (startRef.current === null) return;
   const seconds = (Date.now() - startRef.current) / 1000;
        if (seconds >= minSeconds) {
          tracker.track("dwell", id, Math.min(seconds, 300));
        }
      };
    }, [articleId, minSeconds]);
}
