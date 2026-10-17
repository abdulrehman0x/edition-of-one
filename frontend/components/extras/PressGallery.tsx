"use client";

import { useState } from "react";
import type { PressGallery as PG } from "../../lib/types";

export default function PressGallery({ gallery }: { gallery: PG }) {
 const [open, setOpen] = useState(false);

 return (
  <div style={{ borderTop: "1px solid var(--ink)", paddingTop: 12 }}>
    <button
     type="button"
     onClick={() => setOpen(!open)}
     style={{
       width: "100%",
       background: "transparent",
       border: "none",
       padding: 0,
       textAlign: "left",
       display: "flex",
       justifyContent: "space-between",
       alignItems: "baseline",
     }}
    >
     <h3
       style={{
         fontFamily: "var(--font-playfair)",
         fontSize: 20,
         letterSpacing: "0.2em",
         textTransform: "uppercase",
         margin: 0,
       }}
     >
       Press Gallery
     </h3>
     <span style={{ fontSize: 12, color: "var(--ink-faint)" }}>
       {open ? "▲ close" : "▼ open"}
     </span>
    </button>

    {open && (
     <div style={{ marginTop: 12 }}>
      <p style={{ fontSize: 12, color: "var(--ink-faint)", marginTop: 0 }}>
       Same story, different outlets.
      </p>
      <div style={{ display: "grid", gap: 8 }}>
       {gallery.rows.map((row, idx) => (
             <div
               key={idx}
               style={{
                 border: "1px solid var(--rule)",
                 padding: 12,
                 background: "var(--paper)",
               }}
             >
               <div
                 style={{
                   fontSize: 11,
                   letterSpacing: "0.2em",
                   textTransform: "uppercase",
                   color: "var(--ink-faint)",
                   marginBottom: 4,
                 }}
               >
                 {row.title}
               </div>
               <div style={{ fontSize: 13 }}>{row.caption}</div>
             </div>
           ))}
          </div>
         </div>
       )}
      </div>
    );
}
