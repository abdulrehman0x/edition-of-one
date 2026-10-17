"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getArchive, getEdition } from "../../lib/api";
import { useReader } from "../../lib/reader";
import type { Edition } from "../../lib/types";

interface ArchiveEntry {
  date: string;
  headline: string;
}

export default function ArchivePage() {
 const [readerId] = useReader();
 const [entries, setEntries] = useState<ArchiveEntry[]>([]);
 const [query, setQuery] = useState("");
 const [loading, setLoading] = useState(true);

    useEffect(() => {
  if (!readerId) return;
  let mounted = true;
  (async () => {
    const { dates } = await getArchive(readerId);
    const sliced = dates.slice(0, 30);
    const rich: ArchiveEntry[] = [];
    for (const d of sliced) {
      const res = await getEdition(readerId, d);
      const ed: Edition | null = res.edition;
      rich.push({
        date: d,
        headline: ed?.front?.lead?.title || "Untitled edition",
      });
    }
    if (mounted) {
      setEntries(rich);
      setLoading(false);
    }
  })();
  return () => {
    mounted = false;
  };
}, [readerId]);

const filtered = useMemo(() => {
  const q = query.trim().toLowerCase();
  if (!q) return entries;
  return entries.filter(
    (e) =>
      e.headline.toLowerCase().includes(q) || e.date.includes(q)
  );
}, [entries, query]);

return (
 <div className="page">
   <header style={{ textAlign: "center", marginBottom: 24 }}>
    <h1 style={{ fontFamily: "var(--font-fraktur)", fontSize: 48, margin: 0 }}>
     Archive
    </h1>
    <p
     style={{
       fontSize: 12,
       letterSpacing: "0.3em",
       textTransform: "uppercase",
    color: "var(--ink-faint)",
  }}
 >
  Last 30 editions
 </p>
</header>

<div style={{ marginBottom: 20, maxWidth: 400, margin: "0 auto 24px" }}>
 <input
  placeholder="Search headlines or dates"
  value={query}
  onChange={(e) => setQuery(e.target.value)}
  style={{ width: "100%" }}
 />
</div>

{loading ? (
  <p style={{ textAlign: "center" }}>Scanning the back issues…</p>
):(
  <div
   style={{
     display: "grid",
     gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
     gap: 12,
   }}
  >
   {filtered.map((e) => (
     <Link
       key={e.date}
       href={`/edition/${e.date}`}
       style={{
         border: "1px solid var(--ink)",
         padding: 14,
         background: "var(--paper)",
         color: "var(--ink)",
       }}
     >
       <div
         style={{
           fontSize: 11,
           letterSpacing: "0.2em",
           textTransform: "uppercase",
           color: "var(--ink-faint)",
         }}
              >
                {e.date}
              </div>
              <div
                style={{
                  fontFamily: "var(--font-playfair)",
                  fontSize: 18,
                  marginTop: 6,
                  lineHeight: 1.2,
                }}
              >
                {e.headline}
              </div>
            </Link>
          ))}
          {filtered.length === 0 && (
            <p style={{ textAlign: "center" }}>No editions match your search.</p>
          )}
         </div>
       )}
      </div>
    );
}
