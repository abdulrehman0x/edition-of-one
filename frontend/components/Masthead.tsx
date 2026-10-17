"use client";

import type { Edition } from "../lib/types";

export default function Masthead({ edition }: { edition: Edition }) {
 return (
  <header
    style={{
      textAlign: "center",
      borderBottom: "3px double var(--ink)",
      borderTop: "1px solid var(--ink)",
      padding: "10px 0 12px",
      marginBottom: 20,
    }}
  >
    <h1
      style={{
       fontFamily: "var(--font-fraktur)",
          fontSize: 72,
          margin: 0,
          lineHeight: 1,
          letterSpacing: "0.01em",
        }}
       >
        {edition.nameplate || "Edition of One"}
       </h1>
       <div
        style={{
          fontSize: 11,
          letterSpacing: "0.35em",
          textTransform: "uppercase",
          color: "var(--ink-faint)",
          marginTop: 4,
        }}
       >
        {edition.dateline || edition.date}
       </div>
      </header>
    );
}
