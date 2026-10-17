"use client";

import React, { useState } from "react";

interface MastheadProps {
  reader: string;
  issueNo?: number | string;
  date: string;
  weather?: string;
  onRefresh?: () => void;
}

export default function Masthead({
  reader,
  issueNo,
  date,
  weather,
  onRefresh,
}: MastheadProps) {
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function handleSync() {
    setSyncing(true);
    setMessage(null);
    try {
      const res = await fetch("/api/refresh/" + encodeURIComponent(reader), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) {
        throw new Error("refresh failed (" + res.status + ")");
      }
      const data = await res.json();
      const secondaryCount = (data && data.secondary ? data.secondary.length : 0);
      setMessage("Synced live news: " + secondaryCount + " secondary stories");
      if (onRefresh) onRefresh();
    } catch (err: any) {
      setMessage(err && err.message ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <header className="masthead">
      <div className="masthead-row masthead-strip">
        <span className="masthead-reader">Printed for {reader}</span>
        <span className="masthead-issue">
          No. {issueNo ?? ""} — {date}
        </span>
        <span className="masthead-weather">{weather ?? ""}</span>
      </div>
      <h1 className="masthead-nameplate">Edition of One</h1>
      <div className="masthead-actions">
        <button
          type="button"
          className="sync-btn"
          onClick={handleSync}
          disabled={syncing}
          aria-live="polite"
        >
          {syncing ? "Syncing…" : "🔄 Sync Live News"}
        </button>
        {message ? <span className="sync-msg">{message}</span> : null}
      </div>
    </header>
  );
}
