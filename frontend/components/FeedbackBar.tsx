"use client";

import { useState } from "react";
import { tracker } from "../lib/tracker";

export default function FeedbackBar({ articleId }: { articleId: string }) {
 const [choice, setChoice] = useState<"up" | "down" | "save" | null>(null);

    function handle(kind: "up" | "down" | "save") {
      if (choice === kind) {
        setChoice(null);
        return;
      }
      setChoice(kind);
      if (kind === "up") tracker.track("thumb_up", articleId, 1.0);
      else if (kind === "down") tracker.track("thumb_down", articleId, 1.0);
      else tracker.track("save", articleId, 1.0);
    }

    const btn = (label: string, kind: "up" | "down" | "save") => (
     <button
      key={kind}
      type="button"
      onClick={() => handle(kind)}
      style={{
        border: "1px solid var(--rule)",
        background: choice === kind ? "var(--ink)" : "var(--paper)",
        color: choice === kind ? "var(--paper)" : "var(--ink-soft)",
         fontSize: 10,
         padding: "2px 6px",
         letterSpacing: "0.1em",
         textTransform: "uppercase",
       }}
      >
       {label}
      </button>
    );

    return (
      <div style={{ display: "flex", gap: 4 }}>
       {btn("▲", "up")}
       {btn("▼", "down")}
       {btn("save", "save")}
      </div>
    );
}
