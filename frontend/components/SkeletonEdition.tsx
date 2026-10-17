"use client";

export default function SkeletonEdition() {
  return (
    <div className="page">
      <div
       className="skeleton"
       style={{ height: 80, marginBottom: 24, borderRadius: 2 }}
      />
      <div style={{ display: "grid", gridTemplateColumns: "3fr 1fr", gap: 24 }}>
       <div>
         <div className="skeleton" style={{ height: 44, marginBottom: 12 }} />
         <div className="skeleton" style={{ height: 240 }} />
       </div>
       <div>
         <div className="skeleton" style={{ height: 100, marginBottom: 12 }} />
         <div className="skeleton" style={{ height: 100 }} />
       </div>
      </div>
      <div style={{ marginTop: 32 }}>
       <div className="skeleton" style={{ height: 20, width: 200, marginBottom: 12 }} />
       <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}>
         <div className="skeleton" style={{ height: 120 }} />
         <div className="skeleton" style={{ height: 120 }} />
         <div className="skeleton" style={{ height: 120 }} />
       </div>
      </div>
    </div>
  );
}
