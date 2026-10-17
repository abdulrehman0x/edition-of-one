"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { postOnboarding } from "../lib/api";
import { getReaderId, setReaderId } from "../lib/reader";
import type { Topic } from "../lib/types";

const TOPICS: { id: Topic; label: string }[] = [
 { id: "world", label: "World" },
 { id: "pakistan", label: "Pakistan" },
 { id: "politics", label: "Politics" },
 { id: "business", label: "Business" },
 { id: "markets", label: "Markets" },
 { id: "technology", label: "Technology" },
 { id: "ai", label: "AI" },
  { id: "science", label: "Science" },
  { id: "space", label: "Space" },
  { id: "health", label: "Health" },
  { id: "sport", label: "Sport" },
  { id: "cricket", label: "Cricket" },
  { id: "football", label: "Football" },
  { id: "culture", label: "Culture" },
  { id: "film_music", label: "Film & Music" },
  { id: "education", label: "Education" },
  { id: "climate", label: "Climate" },
  { id: "startups", label: "Startups" },
  { id: "opinion", label: "Opinion" },
];

type LikeLevel = 1 | 2;

export default function OnboardingPage() {
 const router = useRouter();
 const [readerId, setLocalReaderId] = useState("");
 const [likes, setLikes] = useState<Record<string, LikeLevel>>({});
 const [freeText, setFreeText] = useState("");
 const [readingTime, setReadingTime] = useState<"short" | "medium" | "long">("medium");
 const [tone, setTone] = useState<"neutral" | "warm" | "analytical">("neutral");
  const [loading, setLoading] = useState(false);

 useEffect(() => {
   setLocalReaderId(getReaderId());
 }, []);

 function toggleTopic(topic: string, level: LikeLevel) {
   setLikes((prev) => {
     const current = prev[topic];
     if (current === level) {
       const next = { ...prev };
       delete next[topic];
       return next;
     }
     return { ...prev, [topic]: level };
   });
 }

 async function handleSubmit() {
  setLoading(true);
    const loves = Object.keys(likes).filter((k) => likes[k] === 2);
    const interests = [
      ...Object.keys(likes),
      ...(freeText.trim() ? [freeText.trim()] : []),
    ];
    const payload = {
      reader_id: readerId || getReaderId(),
      name: "Reader",
      interests,
      loves,
      reading_time: readingTime,
      location: "Islamabad",
      tone,
    };
    try {
      await postOnboarding(payload);
    } catch {
      /* continue offline */
    }
    setReaderId(payload.reader_id);
    setTimeout(() => router.push("/today"), 400);
}

return (
 <div className="page" style={{ maxWidth: 1100 }}>
   <header style={{ textAlign: "center", marginBottom: 28 }}>
    <h1 style={{ fontFamily: "var(--font-fraktur)", fontSize: 64, margin: 0 }}>
     Edition of One
    </h1>
    <p
     style={{
       fontSize: 12,
       letterSpacing: "0.3em",
       textTransform: "uppercase",
       color: "var(--ink-faint)",
       marginTop: 4,
     }}
    >
     Onboard your daily broadsheet
    </p>
   </header>

     <section style={{ marginBottom: 24 }}>
      <h2 style={{ fontSize: 20, marginBottom: 4 }}>Pick what you read</h2>
      <p style={{ color: "var(--ink-soft)", marginTop: 0, fontSize: 13 }}>
       Tap once to like · tap again to love · tap a third time to clear.
      </p>
      <div
       style={{
        display: "grid",
       gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
       gap: 8,
       marginTop: 12,
     }}
    >
     {TOPICS.map((t) => {
       const level = likes[t.id];
       return (
         <button
          key={t.id}
          type="button"
          onClick={() => toggleTopic(t.id, level === 1 ? 2 : 1)}
          style={{
            border: "1px solid var(--ink)",
            background:
              level === 2
                ? "var(--oxblood)"
                : level === 1
                ? "var(--shade)"
                : "var(--paper)",
            color: level === 2 ? "var(--paper)" : "var(--ink)",
            padding: "10px 8px",
            fontSize: 13,
            letterSpacing: "0.04em",
            textTransform: "uppercase",
            fontWeight: level ? 700 : 400,
            transition: "all 120ms ease",
          }}
         >
          {t.label}
         </button>
       );
     })}
    </div>
   </section>

   <section style={{ marginBottom: 24 }}>
    <label style={{ display: "block", fontSize: 12, letterSpacing: "0.2em", textTransform:
"uppercase" }}>
      Free-text preferences
    </label>
    <textarea
      value={freeText}
      onChange={(e) => setFreeText(e.target.value)}
  rows={3}
  placeholder="e.g. Pakistani politics, cricket, AI and startups"
  style={{ width: "100%", marginTop: 6 }}
 />
</section>

<section style={{ marginBottom: 24 }}>
 <div style={{ fontSize: 12, letterSpacing: "0.2em", textTransform: "uppercase" }}>
  Reading time
 </div>
 <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
  {(["short", "medium", "long"] as const).map((t) => (
    <button
      key={t}
      type="button"
      onClick={() => setReadingTime(t)}
      style={{
        border: "1px solid var(--ink)",
        background: readingTime === t ? "var(--ink)" : "var(--paper)",
        color: readingTime === t ? "var(--paper)" : "var(--ink)",
        padding: "8px 16px",
        fontSize: 12,
        letterSpacing: "0.15em",
        textTransform: "uppercase",
      }}
    >
      {t}
    </button>
  ))}
 </div>
</section>

<section style={{ marginBottom: 24 }}>
 <div style={{ fontSize: 12, letterSpacing: "0.2em", textTransform: "uppercase" }}>
  Tone
 </div>
 <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
  {(["neutral", "warm", "analytical"] as const).map((t) => (
    <label
     key={t}
     style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}
    >
     <input
       type="radio"
        name="tone"
        checked={tone === t}
        onChange={() => setTone(t)}
      />
      {t}
    </label>
  ))}
 </div>
</section>

<div style={{ textAlign: "center" }}>
 <button
  type="button"
  onClick={handleSubmit}
  disabled={loading}
  style={{
    padding: "14px 40px",
    border: "1px solid var(--ink)",
    background: "var(--ink)",
    color: "var(--paper)",
    fontSize: 13,
    letterSpacing: "0.3em",
    textTransform: "uppercase",
  }}
 >
  {loading ? "Setting the presses…" : "Set the presses"}
 </button>
       </div>

       {loading && (
         <div
          style={{
            textAlign: "center",
            marginTop: 24,
            fontSize: 12,
            letterSpacing: "0.3em",
            textTransform: "uppercase",
            color: "var(--ink-faint)",
          }}
         >
          Warming the ink…
         </div>
       )}
      </div>
    );
}
