"use client";

import React, { useRef, useState } from "react";

export interface AudioChapter {
  title: string;
  text: string;
  t_start: number;
  t_end: number;
}

interface AudioBroadcastProps {
  audioUrl: string;
  chapters: AudioChapter[];
}

function formatTime(s: number): string {
  if (!Number.isFinite(s) || s < 0) return "0:00";
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return m + ":" + sec.toString().padStart(2, "0");
}

export default function AudioBroadcast({ audioUrl, chapters }: AudioBroadcastProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [active, setActive] = useState<number>(-1);

  if (!audioUrl) {
    return (
      <div className="audio-broadcast audio-broadcast--empty">
        <div className="audio-title">Audio Broadcast</div>
        <p className="audio-empty">No audio summary for this edition yet.</p>
      </div>
    );
  }

  function seek(idx: number) {
    const el = audioRef.current;
    if (!el || !chapters[idx]) return;
    el.currentTime = chapters[idx].t_start;
    el.play();
    setActive(idx);
  }

  function onTime() {
    const el = audioRef.current;
    if (!el) return;
    const t = el.currentTime;
    const idx = chapters.findIndex((c) => t >= c.t_start && t < c.t_end);
    setActive(idx);
  }

  return (
    <div className="audio-broadcast">
      <div className="audio-title">Audio Broadcast</div>
      <audio
        ref={audioRef}
        src={audioUrl}
        controls
        onTimeUpdate={onTime}
        className="audio-player"
      />
      <ol className="audio-chapters">
        {chapters.map((c, i) => (
          <li
            key={i}
            className={i === active ? "audio-chapter active" : "audio-chapter"}
          >
            <button type="button" onClick={() => seek(i)}>
              <span className="chapter-time">{formatTime(c.t_start)}</span>
              <span className="chapter-title">{c.title}</span>
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
