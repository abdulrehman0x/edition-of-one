"use client";

export default function WhyChip({ text }: { text: string }) {
 return (
  <span
    style={{
     display: "inline-block",
     border: "1px dashed var(--oxblood)",
     color: "var(--oxblood)",
     fontSize: 11,
     padding: "4px 10px",
         letterSpacing: "0.1em",
         fontStyle: "italic",
       }}
      >
       Why: {text}
      </span>
    );
}
