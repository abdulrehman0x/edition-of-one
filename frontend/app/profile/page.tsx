"use client";

import { useEffect, useState } from "react";
import { advanceNight, getProfile, removeTopic as removeTopicApi } from "../../lib/api";
import { useReader } from "../../lib/reader";
import type { Profile } from "../../lib/types";
export default function ProfilePage() {
 const [readerId] = useReader();
 const [profile, setProfile] = useState<Profile | null>(null);
 const [busy, setBusy] = useState(false);
 const [message, setMessage] = useState("");

 async function load() {
   if (!readerId) return;
   const p = await getProfile(readerId);
   setProfile(p);
 }

 useEffect(() => {
   void load();
   // eslint-disable-next-line react-hooks/exhaustive-deps
 }, [readerId]);

 async function handleAdvance() {
   if (!readerId) return;
   setBusy(true);
   setMessage("");
   const ok = await advanceNight(readerId);
   setBusy(false);
   setMessage(
     ok
       ? "Weights re-tuned for tomorrow. Reload the edition to see the changes."
       : "Backend offline — learning is queued locally."
   );
   await load();
 }

 async function removeTopic(topic: string) {
   if (!profile || !readerId) return;
   const updated = await removeTopicApi(readerId, topic);
   if (updated) setProfile(updated);
   else setMessage("Could not reach the backend; topic not removed.");
 }

 if (!profile) {
   return (
     <div className="page">
       <p>No profile yet. Complete onboarding first.</p>
      </div>
    );
}

const topics = Object.entries(profile.weights)
 .map(([k, v]) => [k, v] as [string, number])
 .sort((a, b) => b[1] - a[1]);

return (
 <div className="page">
   <header style={{ textAlign: "center", marginBottom: 24 }}>
    <h1 style={{ fontFamily: "var(--font-fraktur)", fontSize: 48, margin: 0 }}>
     Reader Profile
    </h1>
    <p
     style={{
       fontSize: 12,
       letterSpacing: "0.3em",
       textTransform: "uppercase",
       color: "var(--ink-faint)",
     }}
    >
     {profile.reader_id}
    </p>
   </header>

     <section style={{ marginBottom: 24 }}>
      <h2 style={{ fontSize: 20 }}>Topic weights</h2>
      <div style={{ display: "grid", gap: 6, marginTop: 8 }}>
       {topics.map(([topic, weight]) => {
         const delta = profile.weight_deltas?.[topic] ?? 0;
         const arrow = delta > 0.01 ? "▲" : delta < -0.01 ? "▼" : "·";
         const color =
          delta > 0.01 ? "#1a6b1a" : delta < -0.01 ? "var(--oxblood)" : "var(--ink-faint)";
         return (
          <div
            key={topic}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              borderBottom: "1px solid var(--rule)",
              paddingBottom: 4,
            }}
      >
       <div style={{ flex: 1, textTransform: "capitalize" }}>
        {topic.replace(/_/g, " ")}
       </div>
       <div style={{ width: 200, background: "var(--shade)", height: 8 }}>
        <div
          style={{
            width: `${Math.round(weight * 100)}%`,
            background: "var(--ink)",
            height: 8,
          }}
        />
       </div>
       <div style={{ width: 60, textAlign: "right", fontSize: 12 }}>
        {weight.toFixed(2)}
       </div>
       <div style={{ width: 50, textAlign: "right", color, fontSize: 12 }}>
        {arrow} {delta !== 0 ? delta.toFixed(2) : ""}
       </div>
       <button
        type="button"
        onClick={() => removeTopic(topic)}
        style={{
          border: "1px solid var(--ink)",
          background: "var(--paper)",
          fontSize: 11,
          padding: "2px 6px",
        }}
       >
        remove
       </button>
      </div>
    );
  })}
 </div>
</section>

<section style={{ textAlign: "center", marginTop: 32 }}>
 <button
  type="button"
  onClick={handleAdvance}
  disabled={busy}
  style={{
    padding: "12px 30px",
            border: "1px solid var(--ink)",
            background: "var(--oxblood)",
            color: "var(--paper)",
            fontSize: 12,
            letterSpacing: "0.3em",
            textTransform: "uppercase",
          }}
        >
          {busy ? "Running overnight…" : "Advance one night (demo)"}
        </button>
        {message && (
          <p style={{ marginTop: 12, fontSize: 12, color: "var(--ink-soft)" }}>
            {message}
          </p>
        )}
       </section>
      </div>
    );
}
