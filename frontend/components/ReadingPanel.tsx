"use client";

import { useEffect } from "react";
import type { ArticleRecord } from "../lib/types";
import { useDwell } from "../lib/tracker";

interface Props {
  article: ArticleRecord | null;
  onClose: () => void;
}

export default function ReadingPanel({ article, onClose }: Props) {
 useDwell(article?.id ?? null);

    useEffect(() => {
     if (!article) return;
     function onKey(ev: KeyboardEvent) {
       if (ev.key === "Escape") onClose();
     }
     window.addEventListener("keydown", onKey);
     return () => window.removeEventListener("keydown", onKey);
}, [article, onClose]);

if (!article) return null;

return (
 <div
   role="dialog"
   aria-modal="true"
   onClick={(e) => {
     if (e.target === e.currentTarget) onClose();
   }}
   style={{
     position: "fixed",
     inset: 0,
     background: "rgba(0,0,0,0.35)",
     display: "flex",
     justifyContent: "flex-end",
     zIndex: 100,
   }}
 >
   <div
     style={{
       background: "var(--paper)",
       width: "min(640px, 100%)",
       height: "100%",
       overflowY: "auto",
       padding: 32,
       borderLeft: "3px double var(--ink)",
     }}
   >
     <div
       style={{
         display: "flex",
         justifyContent: "space-between",
         alignItems: "center",
         marginBottom: 16,
       }}
     >
       <span
         style={{
           fontSize: 11,
           letterSpacing: "0.3em",
           textTransform: "uppercase",
           color: "var(--ink-faint)",
    }}
  >
    {article.source}
  </span>
  <button
    type="button"
    onClick={onClose}
    style={{
      border: "1px solid var(--ink)",
      background: "var(--paper)",
      fontSize: 11,
      padding: "2px 8px",
    }}
  >
    Esc
  </button>
</div>
<h2 style={{ fontFamily: "var(--font-playfair)", fontSize: 28, lineHeight: 1.15 }}>
  {article.title}
</h2>
<div
  style={{
    fontFamily: "var(--font-caslon)",
    fontSize: 15,
    lineHeight: 1.6,
  }}
>
  {(article.body.long || article.body.medium || article.body.short)
    .split(/\n\n+/)
    .map((p, i) => (
      <p key={i}>{p}</p>
    ))}
</div>
{article.url && (
  <p style={{ marginTop: 20, fontSize: 12 }}>
    Source:{" "}
    <a href={article.url} target="_blank" rel="noreferrer">
      {article.url}
    </a>
  </p>
)}
<p style={{ marginTop: 24, fontSize: 11, color: "var(--ink-faint)" }}>
  Press <kbd>Esc</kbd> to close
        </p>
       </div>
      </div>
    );
}
