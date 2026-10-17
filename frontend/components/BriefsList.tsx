"use client";

import type { ArticleRecord } from "../lib/types";

interface Props {
  briefs: ArticleRecord[];
  onOpen: (a: ArticleRecord) => void;
}

export default function BriefsList({ briefs, onOpen }: Props) {
 return (
  <div
    style={{
      borderTop: "3px double var(--ink)",
      borderBottom: "1px solid var(--ink)",
      padding: "12px 0",
      columnCount: 4,
      columnGap: 18,
      columnRule: "1px solid var(--rule)",
    }}
  >
    {briefs.map((a) => (
      <div
       key={a.id}
       style={{
         breakInside: "avoid",
         marginBottom: 12,
         paddingBottom: 6,
       }}
       id={`story-${a.id}`}
      >
       <h4
         style={{
           fontFamily: "var(--font-playfair)",
           fontSize: 13,
           margin: "0 0 4px",
         }}
       >
         <button
           type="button"
           onClick={() => onOpen(a)}
           style={{
             background: "none",
             border: "none",
             padding: 0,
             textAlign: "left",
             color: "inherit",
             font: "inherit",
             cursor: "pointer",
           }}
         >
             {a.title}
            </button>
           </h4>
           <p style={{ fontSize: 11, color: "var(--ink-soft)", margin: 0 }}>
            {a.body.short}
           </p>
         </div>
       ))}
      </div>
    );
}
