"use client";
import { useState } from "react";
import type { BackPage as BP } from "../../lib/types";

export default function BackPage({ backPage }: { backPage: BP }) {
 const [answers, setAnswers] = useState<Record<number, number>>({});
 const [struck, setStruck] = useState<Record<string, boolean>>({});

 function selectAnswer(qIdx: number, optIdx: number) {
   setAnswers((prev) => ({ ...prev, [qIdx]: optIdx }));
 }

 const score = Object.entries(answers).filter(([q, a]) => {
   const idx = Number(q);
   return backPage.quiz[idx]?.answer === a;
 }).length;

 function toggleWord(word: string) {
   setStruck((prev) => ({ ...prev, [word]: !prev[word] }));
 }

 return (
  <div style={{ borderTop: "3px double var(--ink)", paddingTop: 20 }}>
    <h2
     style={{
       fontFamily: "var(--font-fraktur)",
       fontSize: 36,
       margin: "0 0 16px",
     }}
    >
     The Back Page
    </h2>

   {backPage.quiz.length > 0 && (
    <section style={{ marginBottom: 32 }}>
     <h3
      style={{
        fontFamily: "var(--font-playfair)",
        fontSize: 20,
        letterSpacing: "0.2em",
        textTransform: "uppercase",
      }}
     >
      News Quiz · {score} / {backPage.quiz.length}
</h3>
<ol style={{ paddingLeft: 0, listStyle: "none" }}>
 {backPage.quiz.map((q, qi) => (
  <li
    key={qi}
    style={{
      borderTop: "1px solid var(--rule)",
      padding: "10px 0",
    }}
  >
    <div style={{ fontFamily: "var(--font-playfair)", fontSize: 16 }}>
      {qi + 1}. {q.question}
    </div>
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 6 }}>
      {q.options.map((opt, oi) => {
        const chosen = answers[qi] === oi;
        const correct = q.answer === oi;
        const reveal = answers[qi] !== undefined;
        return (
          <button
           key={oi}
           type="button"
           onClick={() => selectAnswer(qi, oi)}
           style={{
             border: "1px solid var(--ink)",
             padding: "4px 10px",
             fontSize: 12,
             background: chosen
              ? reveal && correct
                ? "#1a6b1a"
                : reveal
                ? "var(--oxblood)"
                : "var(--ink)"
              : reveal && correct
              ? "#d6e6d6"
              : "var(--paper)",
             color: chosen ? "var(--paper)" : "var(--ink)",
           }}
          >
           {opt}
          </button>
        );
      })}
    </div>
      </li>
    ))}
   </ol>
  </section>
)}

{backPage.word_search && (
 <section style={{ marginBottom: 32 }}>
  <h3
   style={{
     fontFamily: "var(--font-playfair)",
     fontSize: 20,
     letterSpacing: "0.2em",
     textTransform: "uppercase",
   }}
  >
   Word Search
  </h3>
  <div
   style={{
     display: "grid",
     gridTemplateColumns: `repeat(${backPage.word_search.grid[0]?.length || 12}, 1fr)`,
     fontFamily: "monospace",
     fontSize: 12,
     gap: 2,
     maxWidth: 360,
   }}
  >
   {backPage.word_search.grid.flatMap((row, ri) =>
     row.split("").map((ch, ci) => (
       <div
        key={`${ri}-${ci}`}
        style={{
          border: "1px solid var(--rule)",
          textAlign: "center",
          padding: "4px 0",
        }}
       >
        {ch}
       </div>
     ))
   )}
  </div>
  <div style={{ marginTop: 10, display: "flex", gap: 6, flexWrap: "wrap" }}>
    {backPage.word_search.words.map((w) => (
      <button
        key={w}
        type="button"
        onClick={() => toggleWord(w)}
        style={{
          border: "1px solid var(--rule)",
          background: "transparent",
          textDecoration: struck[w] ? "line-through" : "none",
          fontSize: 11,
          padding: "2px 8px",
        }}
      >
        {w}
      </button>
    ))}
   </div>
  </section>
)}

{backPage.on_this_day.length > 0 && (
 <section>
  <h3
   style={{
     fontFamily: "var(--font-playfair)",
     fontSize: 20,
     letterSpacing: "0.2em",
     textTransform: "uppercase",
   }}
  >
   From History
  </h3>
  <ul style={{ listStyle: "none", padding: 0 }}>
   {backPage.on_this_day.map((item, i) => (
     <li
       key={i}
       style={{
         borderTop: "1px solid var(--rule)",
         padding: "8px 0",
         fontSize: 13,
       }}
     >
       <strong style={{ color: "var(--oxblood)" }}>{item.year ?? "—"}</strong>{" "}
       — {item.text}
             </li>
           ))}
          </ul>
         </section>
       )}
      </div>
    );
}
