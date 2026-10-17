"use client";

export default function SectionHeader({ name }: { name: string }) {
 return (
   <h2
    style={{
      fontFamily: "var(--font-playfair)",
      fontSize: 24,
      letterSpacing: "0.2em",
      textTransform: "uppercase",
      borderBottom: "2px solid var(--ink)",
      paddingBottom: 4,
      margin: "0 0 12px",
    }}
   >
    {name}
   </h2>
 );
}
