"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE } from "../../lib/api";
import type { Edition } from "../../lib/types";

export default function AudioPlayer({ edition }: { edition: Edition }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [audioFailed, setAudioFailed] = useState(false);

  const bc = edition.broadcast;
  const audioUrl = bc?.audio_url ? `${API_BASE}${bc.audio_url}` : null;
  const speechMode = !audioUrl || audioFailed;
  const chapters = bc?.chapters ?? [];
  const total = Math.round(bc?.duration ?? 0);

  // Stop any speech when the edition changes or the player unmounts.
  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, [edition.id]);

  function speak(): boolean {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return false;
    const lead = edition.front.lead;
    const parts: string[] = bc?.script
      ? [
          bc.script.intro,
          ...bc.script.chapters.map((c) => `${c.title}. ${c.script}`),
          bc.script.outro,
        ]
      : lead
      ? [`${lead.title}. ${lead.body.short}`]
      : [];
    if (parts.length === 0) return false;
    window.speechSynthesis.cancel();
    parts.forEach((text, i) => {
      const utter = new SpeechSynthesisUtterance(text);
      if (i === parts.length - 1) utter.onend = () => setPlaying(false);
      window.speechSynthesis.speak(utter);
    });
    return true;
  }

  function toggle() {
    if (playing) {
      if (speechMode) window.speechSynthesis?.cancel();
      else audioRef.current?.pause();
      setPlaying(false);
      return;
    }
    if (speechMode) {
      if (speak()) setPlaying(true);
      return;
    }
    audioRef.current
      ?.play()
      .then(() => setPlaying(true))
      .catch(() => {
        setAudioFailed(true);
        if (speak()) setPlaying(true);
      });
  }

  function seek(start: number) {
    const el = audioRef.current;
    if (!el || speechMode) return;
    el.currentTime = start;
    void el.play().then(() => setPlaying(true));
  }

  function jumpTo(id: string) {
    const el = document.getElementById(`story-${id}`);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const stories = [
    ...(edition.front.lead ? [edition.front.lead] : []),
    ...edition.front.secondary,
  ];

  return (
    <div style={{ border: "1px solid var(--ink)", padding: 12, background: "var(--paper)" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 8,
        }}
      >
        <div style={{ fontSize: 12, letterSpacing: "0.25em", textTransform: "uppercase" }}>
          The Morning Broadcast
        </div>
        <button
          type="button"
          onClick={toggle}
          style={{
            border: "1px solid var(--ink)",
            background: "var(--ink)",
            color: "var(--paper)",
            padding: "4px 14px",
            fontSize: 11,
            letterSpacing: "0.2em",
            textTransform: "uppercase",
          }}
        >
          {playing ? "❚❚ Pause" : "▶ Play"}
        </button>
      </div>
      <div style={{ fontSize: 11, color: "var(--ink-faint)" }}>
        {speechMode
          ? "Read aloud by your browser's speech synthesis."
          : `${total}s · ${chapters.length} chapters`}
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
        {stories.map((a, i) => (
          <button
            key={a.id}
            type="button"
            onClick={() => (speechMode || !chapters[i] ? jumpTo(a.id) : seek(chapters[i].start))}
            style={{
              border: "1px solid var(--rule)",
              background: "transparent",
              fontSize: 10,
              padding: "2px 8px",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
            }}
          >
            → {a.title.length > 28 ? a.title.slice(0, 28) + "…" : a.title}
          </button>
        ))}
      </div>
      {audioUrl && (
        <audio
          ref={audioRef}
          src={audioUrl}
          preload="none"
          style={{ display: "none" }}
          onEnded={() => setPlaying(false)}
          onError={() => setAudioFailed(true)}
        />
      )}
    </div>
  );
}
