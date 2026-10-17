"use client";

export default function OfflineBanner() {
  return (
    <div
      style={{
        background: "var(--oxblood)",
        color: "var(--paper)",
        textAlign: "center",
        fontSize: 11,
        letterSpacing: "0.3em",
        textTransform: "uppercase",
        padding: "6px 0",
      }}
    >
      Offline — showing cached sample edition
    </div>
  );
}
